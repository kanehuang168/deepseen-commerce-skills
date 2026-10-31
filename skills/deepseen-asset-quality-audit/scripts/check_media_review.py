"""Check a review against actual local media. No model, network, state or billing writes."""
import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def probe_media(path):
    path = Path(path).resolve(strict=True)
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    result = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format',
                             '-of', 'json', str(path)], capture_output=True, timeout=60, check=True)
    data = json.loads(result.stdout)
    duration = float(data.get('format', {}).get('duration', 'nan'))
    if not number(duration) or duration <= 0:
        raise ValueError('媒体时长无效')
    decoded = subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-i', str(path),
                              '-map', '0:v?', '-map', '0:a?', '-f', 'null', '-'],
                             capture_output=True, timeout=180)
    streams = data.get('streams', [])
    return dict(sha256=digest.hexdigest(), durationSeconds=duration,
                videoTracks=sum(s.get('codec_type') == 'video' for s in streams),
                audioTracks=sum(s.get('codec_type') == 'audio' for s in streams),
                fullDecodePassed=decoded.returncode == 0)


def check_review(media, review):
    """Facts are independently probed; semantic observations remain caller evidence."""
    if not isinstance(review, dict) or not isinstance(review.get('authority', {}), dict) or not isinstance(review.get('observation', {}), dict):
        raise ValueError('审核输入必须包含结构化确认要求与实际观察')
    rows = []
    def add(key, state, reason):
        rows.append(dict(id=key, status=state, reasonZh=reason))
    authority = review.get('authority', {})
    observation = review.get('observation', {})
    bound = (isinstance(media.get('sha256'), str) and len(media['sha256']) == 64
             and observation.get('mediaSha256') == media['sha256']
             and isinstance(authority.get('scriptHash'), str) and len(authority['scriptHash']) == 64
             and observation.get('scriptHash') == authority['scriptHash'])
    if not bound:
        add('binding', 'NEEDS_EVIDENCE', '成片或确认稿指纹不匹配，旧审核不能用于当前结果')
    if media.get('fullDecodePassed') is not True or not media.get('videoTracks'):
        add('technical', 'FAIL', '视频缺失或完整解码未通过')
    else:
        add('technical', 'PASS', '实际视频完整解码通过；不代表内容合格')
    audio_mode = authority.get('audioMode', 'UNSPECIFIED')
    tracks = media.get('audioTracks')
    conflict = tracks == 0 and observation.get('speechPresent') is True
    if conflict:
        add('audioObservation', 'NEEDS_EVIDENCE', '实际没有音轨，与审核声称有人声相矛盾')
    if audio_mode == 'SILENT' and tracks == 0:
        add('audio', 'PASS' if bound else 'NEEDS_EVIDENCE', '无音轨符合明确静默要求；画面另行审核')
    elif audio_mode in ('SPEECH', 'ENVIRONMENT') and tracks == 0:
        add('audio', 'FAIL' if bound else 'NEEDS_EVIDENCE', '确认要求的声音无法存在于无音轨成片中')
    elif (bound and audio_mode == 'SPEECH' and observation.get('audioCoverage') == 'FULL'
          and observation.get('speechPresent') is False):
        add('audio', 'FAIL', '完整听审记录未观察到确认要求的人声')
    elif (audio_mode in ('SPEECH', 'ENVIRONMENT', 'SILENT') and bound and not conflict
          and (audio_mode != 'SPEECH' or type(observation.get('speechPresent')) is bool)
          and observation.get('audioCoverage') == 'FULL'
          and type(observation.get('audioMatchesRequirement')) is bool):
        add('audio', 'PASS' if observation['audioMatchesRequirement'] else 'FAIL', '按完整音频观察记录核对；音轨存在本身不证明语义通过')
    else:
        add('audio', 'NEEDS_EVIDENCE', '声音要求或全片声音观察不足；不把低音量当静默')
    if observation.get('videoCoverage') != 'FULL':
        add('visualObservation', 'NEEDS_EVIDENCE', '缺少完整画面观察，不能宣布全片质量通过')
    requirements = authority.get('checks', [])
    if not isinstance(requirements, list) or not requirements:
        requirements = []
        add('visual', 'NEEDS_EVIDENCE', '缺少确认要求及逐项观察，不自动判通过')
    observations = observation.get('checks', [])
    if not isinstance(observations, list):
        observations = []
    known = [r.get('id') for r in requirements if isinstance(r, dict)]
    if len(known) != len(requirements) or len(set(known)) != len(known) or not all(isinstance(x, str) and x for x in known):
        raise ValueError('确认检查必须有唯一稳定编号')
    seen = [r.get('id') for r in observations if isinstance(r, dict)]
    if len(seen) != len(observations) or len(set(seen)) != len(seen):
        raise ValueError('观察检查编号无效或重复')
    by_id = {r['id']: r for r in observations}
    for requirement in requirements:
        key = requirement['id']
        if requirement.get('applies') is False:
            add(key, 'NOT_APPLICABLE', '该项不属于当前确认要求，不据此判成片失败')
            continue
        item = by_id.get(key, {})
        if requirement.get('applies') is not True or not bound:
            add(key, 'NEEDS_EVIDENCE', '检查适用性或当前产物关联尚未确认')
            continue
        evidence = item.get('evidence', {})
        if not isinstance(evidence, dict):
            evidence = {}
        start, end = evidence.get('startSec'), evidence.get('endSec')
        valid = (evidence.get('kind') == 'OBSERVED' and isinstance(evidence.get('descriptionZh'), str)
                 and bool(evidence['descriptionZh'].strip()) and number(start) and number(end)
                 and number(media.get('durationSeconds')) and 0 <= start <= end <= media['durationSeconds'])
        if not valid:
            add(key, 'NEEDS_EVIDENCE', '缺少实际观察位置或证据，计划文字不能代替成片')
            continue
        window = requirement.get('eventWindowSeconds')
        if window is not None:
            if not isinstance(window, list) or len(window) != 2 or not all(number(x) for x in window) or not 0 <= window[0] <= window[1] <= media['durationSeconds']:
                raise ValueError('时间窗须来自确认要求且位于成片时长内')
            actual = item.get('observedEventSec')
            if not number(actual) or not start <= actual <= end:
                add(key, 'NEEDS_EVIDENCE', '关键事件尚无有效实际时间定位')
                continue
            if not window[0] <= actual <= window[1]:
                add(key, 'FAIL', '实际关键事件早于或晚于确认时间窗')
                continue
        if item.get('status') == 'FAIL':
            add(key, 'FAIL', '实际观察记录存在与确认要求矛盾的缺陷')
        elif item.get('status') == 'PASS' and observation.get('videoCoverage') == 'FULL':
            add(key, 'PASS', '完整画面观察记录支持该项；仍以观察来源可靠性为限')
        else:
            add(key, 'NEEDS_EVIDENCE', '抽帧可发现缺陷，不能据此证明全片连续性通过')
    status = ('needs_repair' if any(r['status'] == 'FAIL' for r in rows) else
              'unverified' if any(r['status'] == 'NEEDS_EVIDENCE' for r in rows) else 'passed')
    return dict(status=status, checks=rows, mediaSha256=media.get('sha256'),
                evidenceScope='MEDIA_FACTS_AND_OBSERVATION_CONTRACT', newModelCalls=0,
                noticeZh='仅验证实际媒体技术事实和所供观察契约；不替代完整观看、听审、独立质量评审或用户确认。')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--media', type=Path, required=True)
    parser.add_argument('--review', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('回执已存在，不覆盖历史证据')
    try:
        media = probe_media(args.media)
        result = check_review(media, json.loads(args.review.read_text(encoding='utf8')))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x', encoding='utf8') as stream:
            json.dump(dict(media=media, review=result), stream, ensure_ascii=False, indent=2)
        print(result['status'])
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print('媒体采集或检查失败：' + type(error).__name__)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
