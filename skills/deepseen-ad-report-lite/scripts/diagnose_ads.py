"""Local ad-report arithmetic. Standard library only; no network or account changes."""
from __future__ import annotations

import argparse
import csv
from decimal import Decimal, InvalidOperation
import html
import io
import json
from pathlib import Path
import posixpath
import re
import statistics
import sys
import xml.etree.ElementTree as ET
import zipfile

VERSION = '1.2.1'
MAX_ROWS = 5000
MONEY = ('spend', 'revenue')
COUNTS = ('impressions', 'clicks', 'orders', 'click_orders')
NUMERIC = MONEY + COUNTS
SCOPES = ('currency', 'product', 'account', 'period', 'attribution', 'click_scope')
ALIASES = {
    'creative': ['素材ID', '素材名称', '素材', 'creative_id', 'creative', 'ad_id'],
    'spend': ['消耗', '花费', '广告消耗', 'spend', 'cost'],
    'impressions': ['展示次数', '展示量', '展示', 'impressions'],
    'clicks': ['点击次数', '点击量', '点击', 'clicks', 'destination_clicks'],
    'orders': ['订单数', '订单', '购买数', 'purchases', 'orders'],
    'click_orders': ['点击归因订单数', 'click_attributed_orders'],
    'revenue': ['广告归因成交金额', '成交金额', '销售额', 'revenue'],
    'currency': ['币种', 'currency'], 'product': ['商品ID', '商品', 'product_id'],
    'account': ['账户', '广告账户', 'account', 'account_id'],
    'period': ['统计期', '统计周期', '日期', 'period', 'date'],
    'attribution': ['归因窗口', '归因口径', 'attribution_window'],
    'click_scope': ['点击口径', 'click_scope'],
}
LABELS = dict(zip(NUMERIC, ['消耗', '成交金额', '展示次数', '点击次数', '订单数', '点击归因订单数']))
NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def load_table(path: Path, sheet: str | None = None):
    if path.stat().st_size > 10 * 1024 * 1024:
        raise ValueError('文件超过10MB，请只导出本次分析所需字段。')
    if path.suffix.lower() == '.csv':
        raw = path.read_bytes()
        try:
            text = raw.decode('utf-8-sig')
        except UnicodeDecodeError:
            text = raw.decode('gb18030')
        try:
            dialect = csv.Sniffer().sniff(text[:8192], delimiters=',;\t')
        except csv.Error:
            dialect = csv.excel
        rows = list(csv.reader(io.StringIO(text), dialect))
        name = 'CSV'
    elif path.suffix.lower() == '.xlsx':
        with zipfile.ZipFile(path) as archive:
            if len(archive.infolist()) > 1000 or sum(item.file_size for item in archive.infolist()) > 20 * 1024 * 1024:
                raise ValueError('工作簿展开后过大，请导出所需工作表为CSV。')
            workbook = ET.fromstring(archive.read('xl/workbook.xml'))
            sheets = workbook.findall('m:sheets/m:sheet', NS)
            selected = next((item for item in sheets if sheet is None or item.get('name') == sheet), None)
            if selected is None:
                raise ValueError('找不到指定工作表：' + str(sheet))
            name = selected.get('name', '未命名工作表')
            rid = selected.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
            relations = ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))
            rel = next((item for item in relations if item.get('Id') == rid), None)
            if rel is None or rel.get('TargetMode') == 'External':
                raise ValueError('不读取外部工作表链接，请导出为本地CSV。')
            target = rel.get('Target', '')
            target = posixpath.normpath(target.lstrip('/') if target.startswith('/') else 'xl/' + target)
            if not target.startswith('xl/') or '..' in target.split('/'):
                raise ValueError('工作表路径无效。')
            strings = []
            if 'xl/sharedStrings.xml' in archive.namelist():
                strings = [''.join(item.itertext()) for item in ET.fromstring(archive.read('xl/sharedStrings.xml')).findall('m:si', NS)]
            rows = []
            for row in ET.fromstring(archive.read(target)).findall('m:sheetData/m:row', NS):
                cells = {}
                for cell in row.findall('m:c', NS):
                    letters = re.match(r'[A-Z]+', cell.get('r', ''))
                    if not letters:
                        raise ValueError('工作表缺少单元格坐标。')
                    column = 0
                    for letter in letters[0]:
                        column = column * 26 + ord(letter) - 64
                    if column > 200:
                        raise ValueError('报表列数超过200，请只导出所需字段。')
                    value = cell.findtext('m:v', '', NS)
                    kind = cell.get('t')
                    if cell.find('m:f', NS) is not None:
                        value = {'formula': True}
                    elif kind == 's':
                        value = strings[int(value)]
                    elif kind == 'inlineStr':
                        value = ''.join(cell.find('m:is', NS).itertext())
                    elif kind == 'e':
                        value = ''
                    cells[column - 1] = value
                rows.append([cells.get(index, '') for index in range(max(cells, default=-1) + 1)])
                if len(rows) > MAX_ROWS + 1:
                    raise ValueError('明细超过5000行，请分批导出；本次未截断分析。')
    else:
        raise ValueError('仅支持CSV或XLSX；请将旧格式导出为CSV/XLSX。')
    rows = [row for row in rows if any(str(value).strip() for value in row)]
    if len(rows) < 2:
        raise ValueError('请提供表头及至少一行实际数据。')
    if len(rows) > MAX_ROWS + 1:
        raise ValueError('明细超过5000行，请分批导出；本次未截断分析。')
    return rows, name


def normalize(value):
    return re.sub(r'[\s_()（）-]+', '', str(value)).lower()


def parse_number(value, field, line, warnings):
    if isinstance(value, dict):
        warnings.append(f'数据行{line}的{LABELS[field]}为公式，不执行或采用旧缓存；请导出数值。')
        return None
    text = str(value).strip()
    if text.lower() in ('', '-', '--', 'n/a', 'na', 'null', '未取得', '未提供'):
        return None
    text = re.sub(r'^(USD|CNY|EUR|GBP|RMB|[$¥￥€£])\s*', '', text, flags=re.I).replace(',', '')
    try:
        number = Decimal(text)
        if (not number.is_finite() or number < 0 or number > Decimal('1e18')
                or (number != 0 and number < Decimal('1e-12'))
                or (field in COUNTS and number != number.to_integral_value())):
            raise InvalidOperation
        return number
    except InvalidOperation:
        warnings.append(f'数据行{line}的{LABELS[field]}不是支持范围内的有效非负数（0或10的-12至18次方；次数需为整数），未按0处理。')
        return None


def ratio(a, b, multiplier=1):
    return None if a is None or b is None or b == 0 else a / b * multiplier


def metrics(row):
    return {
        'ctr': ratio(row['clicks'], row['impressions'], 100),
        'click_cvr': ratio(row['click_orders'], row['clicks'], 100),
        'orders_per_click': ratio(row['orders'], row['clicks'], 100),
        'cpc': ratio(row['spend'], row['clicks']),
        'cpm': ratio(row['spend'], row['impressions'], 1000),
        'cpa': ratio(row['spend'], row['orders']),
        'roas': ratio(row['revenue'], row['spend']),
    }


def analyze(table, sheet='CSV', target_roas=None, target_cpa=None):
    warnings, mapping = [], {}
    header = table[0]
    for field, aliases in ALIASES.items():
        hits = [index for index, value in enumerate(header) if normalize(value) in {normalize(alias) for alias in aliases}]
        if len(hits) > 1 and field in NUMERIC:
            raise ValueError(f'多个列对应同一字段“{field}”，请先确认保留哪个口径。')
        if hits:
            mapping[field] = next(index for alias in aliases for index in hits if normalize(header[index]) == normalize(alias))
            if len(hits) > 1:
                warnings.append(f'识别字段“{field}”存在多列，使用“{header[mapping[field]]}”，其余列未参与分组或计算。')
    if not any(field in mapping for field in NUMERIC):
        raise ValueError('未识别到原始指标。请至少提供消耗、展示次数、点击次数、订单数或成交金额一列。')
    missing = [LABELS[field] for field in NUMERIC if field not in mapping]
    if missing:
        warnings.append('未提供字段：' + '、'.join(missing) + '；受影响的计算不补零。')
    rows, seen, duplicate_count, total_count = [], set(), 0, 0
    for line, source in enumerate(table[1:], 2):
        if not any(str(value).strip() for value in source):
            continue
        key = json.dumps(source, ensure_ascii=False, sort_keys=True)
        if key in seen:
            duplicate_count += 1
            continue
        seen.add(key)
        values = {field: source[index] if index < len(source) else '' for field, index in mapping.items()}
        if str(source[0]).strip().lower() in ('合计', '总计', 'total', 'grand total'):
            total_count += 1
            continue
        row = {field: parse_number(values.get(field, ''), field, line, warnings) for field in NUMERIC}
        row.update({field: str(values.get(field, '')).strip() or '未注明' for field in SCOPES})
        row['currency'] = row['currency'].upper() if row['currency'] != '未注明' else '未注明'
        if row['currency'] == '未注明':
            symbols = {sign for field in MONEY for sign in '$¥￥€£' if sign in str(values.get(field, ''))}
            if symbols:
                row['currency'] = '/'.join(sorted(symbols)) + '（币种未注明）'
        if 'clicks' in mapping and normalize(header[mapping['clicks']]) == 'destinationclicks' and row['click_scope'] == '未注明':
            row['click_scope'] = '目的地点击'
        row['creative'] = str(values.get('creative', '')).strip() or f'数据行{line}'
        row['line'] = line
        row['metrics'] = metrics(row)
        row['findings'] = []
        rows.append(row)
    if not rows:
        raise ValueError('没有可分析的明细数据，合计行不能替代素材明细。')
    if duplicate_count:
        warnings.append(f'忽略{duplicate_count}行完全重复记录，未重复累加。')
    if total_count:
        warnings.append(f'忽略{total_count}行合计记录，避免与明细重复累加。')
    groups = {}
    for row in rows:
        groups.setdefault(tuple(row[field] for field in SCOPES), []).append(row)
    if target_cpa is not None and len({row['currency'] for row in rows}) > 1:
        raise ValueError('文件包含多种币种，不能套用同一个目标每单花费；请分币种分析。')
    output_groups = []
    for key, members in groups.items():
        coverage = {field: sum(row[field] is not None for row in members) for field in NUMERIC}
        known = {field: sum((row[field] for row in members if row[field] is not None), Decimal(0)) for field in NUMERIC}
        complete = {field: known[field] if coverage[field] == len(members) else None for field in NUMERIC}
        comparable = [row for row in members if row['metrics']['roas'] is not None]
        median_roas = statistics.median([row['metrics']['roas'] for row in comparable]) if len(comparable) >= 3 else None
        for row in members:
            spend, orders, roas = row['spend'], row['orders'], row['metrics']['roas']
            if spend is not None and spend > 0 and orders == 0:
                row['findings'].append({'code': 'spend_without_orders', 'priority': 1,
                    'observation': f'消耗{fmt(spend)}，记录订单0笔。',
                    'action': '先核对订单回传与归因是否完整，再检查商品、页面和结账流程；当前数据不能证明素材无效。'})
            if target_roas is not None and roas is not None and roas < target_roas:
                row['findings'].append({'code': 'below_target_roas', 'priority': 1,
                    'observation': f'广告回报{fmt(roas)}倍，低于用户目标{fmt(target_roas)}倍。',
                    'action': '比较点击与订单数据，选择一个页面或素材假设复测；没有成本资料，不能据此判断净亏损。'})
            if target_cpa is not None and row['metrics']['cpa'] is not None and row['metrics']['cpa'] > target_cpa:
                row['findings'].append({'code': 'above_target_cpa', 'priority': 1,
                    'observation': f'每单广告花费{fmt(row["metrics"]["cpa"])}，超过用户目标{fmt(target_cpa)}。',
                    'action': '先核对购买事件与金额币种，再定位点击到成交环节；不直接改变广告账户。'})
            if median_roas is not None and roas is not None and roas < median_roas:
                row['findings'].append({'code': 'below_sample_median', 'priority': 2,
                    'observation': f'广告回报{fmt(roas)}倍，低于本组{len(comparable)}行的中位数{fmt(median_roas)}倍。',
                    'action': '仅作本次同范围报表的优先核查线索，不代表行业落后或统计显著。'})
            if orders == 1:
                row['findings'].append({'code': 'one_order', 'priority': 2,
                    'observation': '当前仅记录1笔订单。', 'action': '先复测成交表现，不能把一单结果当作稳定放量依据。'})
        output_groups.append({'scope': dict(zip(SCOPES, key)), 'rows': members, 'row_count': len(members),
                              'known_totals': known, 'coverage': coverage, 'metrics': metrics(complete)})
    if any(row[field] == '未注明' for row in rows for field in SCOPES):
        warnings.append('部分币种、商品、账户、统计期、归因窗口或点击口径未注明；分组相同不证明原始口径相同。')
    return {'version': VERSION, 'execution': '本地计算，未调用DeepSeen', 'sheet': sheet, 'row_count': len(rows),
            'targets': {'roas': target_roas, 'cpa': target_cpa}, 'warnings': list(dict.fromkeys(warnings)), 'groups': output_groups}


def fmt(value):
    return '未计算' if value is None else format(value, '.4f').rstrip('0').rstrip('.') if isinstance(value, Decimal) else str(value)


def safe(value):
    text = html.escape(str(value)).replace('\\', '\\\\').replace('\n', ' ').replace('\r', ' ')
    return re.sub(r'([|`*\[\]!])', r'\\\1', text)


def render(report):
    lines = ['# 投流报表基础诊断', '', report['execution'] + '，未修改投放账户。', '',
             f'工作表：{safe(report["sheet"])}；有效明细{report["row_count"]}行，共{len(report["groups"])}个统计范围。', '',
             '本报告使用用户提供的报表；ROAS为成交金额/广告消耗，不是净利润。未提供目标时不判定达标与否。', '', '## 优先核查', '']
    if report.get('data_kind') == '虚构示例':
        lines.insert(2, '**以下为包内虚构示例，不是用户实际投放结果。**\n')
        lines = [line.replace('本报告使用用户提供的报表', '本报告使用包内虚构样本') for line in lines]
    targets = report['targets']
    if targets['roas'] is not None or targets['cpa'] is not None:
        descriptions = []
        if targets['roas'] is not None:
            descriptions.append('广告回报' + fmt(targets['roas']) + '倍')
        if targets['cpa'] is not None:
            descriptions.append('每单广告花费' + fmt(targets['cpa']))
        lines.insert(-2, '用户目标：' + '；'.join(descriptions) + '。\n')
    findings = []
    for group in report['groups']:
        flagged = [row for row in group['rows'] if row['findings']]
        flagged.sort(key=lambda row: (min(item['priority'] for item in row['findings']), -(row['spend'] or Decimal(0))))
        for row in flagged:
            finding = min(row['findings'], key=lambda item: item['priority'])
            findings.append((finding, row))
    for finding, row in findings[:3]:
        lines.append(f'- **{safe(row["creative"])}**（{safe(row["currency"])}，{safe(row["period"])}）：{safe(finding["observation"])} {safe(finding["action"])}')
    if not findings:
        lines.append('当前可计算数据没有触发已定义核查项；这不等于已证明投放健康。先检查下面的字段覆盖和实际目标。')
    for number, group in enumerate(report['groups'], 1):
        scope = group['scope']
        lines += ['', f'## 范围{number}：{safe(scope["currency"])} · {safe(scope["product"])}', '',
                  '账户：' + safe(scope['account']) + '；统计期：' + safe(scope['period']) + '；归因：' + safe(scope['attribution']) + '；点击口径：' + safe(scope['click_scope']), '',
                  '| 原始指标 | 已知合计 | 有数据行/总行 |', '|---|---:|---:|']
        for field in NUMERIC:
            count = group['coverage'][field]
            lines.append(f'| {LABELS[field]} | {fmt(group["known_totals"][field]) if count else "未提供"} | {count}/{group["row_count"]} |')
        lines += ['', '汇总广告回报：' + fmt(group['metrics']['roas']) + '；汇总报表点击率：' + fmt(group['metrics']['ctr']) + '%。', '',
                  '| 素材 | 消耗 | 点击 | 订单 | 成交金额 | 点击率% | 订单/点击比% | 点击转化率% | 每单花费 | ROAS |',
                  '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
        for row in group['rows']:
            values = [row['creative'], row['spend'], row['clicks'], row['orders'], row['revenue'], row['metrics']['ctr'],
                      row['metrics']['orders_per_click'], row['metrics']['click_cvr'], row['metrics']['cpa'], row['metrics']['roas']]
            lines.append('| ' + ' | '.join(safe(fmt(value)) for value in values) + ' |')
    lines += ['', '## 口径与缺口', '', *('- ' + safe(warning) for warning in report['warnings']), '',
              '- 不同范围分开计算，缺失不补零，分母为0不计算，汇总不平均各行比例。',
              '- 订单/点击比可能包含浏览归因订单，不能直接当点击转化率；点击转化率只使用明确的点击归因订单。',
              '- 这是报表观察和待验证假设，未证明素材、页面或出价是原因；归因未结束时不能把当前0订单当成最终失败。', '',
              '## 公式', '',
              '- 报表点击率 = 点击/展示×100%；点击转化率 = 点击归因订单/点击×100%。',
              '- 订单/点击比 = 全部归因订单/点击×100%；每次点击花费 = 消耗/点击。',
              '- 每千次展示花费 = 消耗/展示×1000；每单广告花费 = 消耗/订单；广告回报ROAS = 广告归因成交金额/消耗。', '']
    return '\n'.join(lines)


def json_number(value):
    if isinstance(value, Decimal):
        return float(value)
    raise TypeError('不支持的数据类型')


def positive(text):
    try:
        value = Decimal(text)
        if not value.is_finite() or value <= 0:
            raise InvalidOperation
        return value
    except InvalidOperation:
        raise argparse.ArgumentTypeError('目标必须是大于0的有限数值。')


def main():
    parser = argparse.ArgumentParser(description='本地广告报表基础诊断，不联网、不调用付费接口。')
    parser.add_argument('input', type=Path)
    parser.add_argument('--sheet')
    parser.add_argument('--target-roas', type=positive)
    parser.add_argument('--target-cpa', type=positive)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--json-output', type=Path)
    parser.add_argument('--demo', action='store_true', help='将输入和报告明确标为虚构演示数据')
    args = parser.parse_args()
    try:
        for output in [args.output, args.json_output]:
            if output and output.resolve() == args.input.resolve():
                raise ValueError('输出不能覆盖原报表。')
            if output and output.exists():
                raise ValueError('输出文件已存在，请使用新文件名以保留历史报告。')
        if args.output and args.json_output and args.output.resolve() == args.json_output.resolve():
            raise ValueError('Markdown与JSON输出路径不能相同。')
        table, sheet = load_table(args.input, args.sheet)
        report = analyze(table, sheet, args.target_roas, args.target_cpa)
        report['data_kind'] = '虚构示例' if args.demo else '用户提供数据'
        markdown = render(report)
        if args.output:
            args.output.write_text(markdown, encoding='utf-8')
        if args.json_output:
            args.json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=json_number), encoding='utf-8')
        print(markdown)
        return 0
    except (ValueError, OSError, csv.Error, KeyError, IndexError, zipfile.BadZipFile, ET.ParseError, UnicodeError) as error:
        print('未完成分析：' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
