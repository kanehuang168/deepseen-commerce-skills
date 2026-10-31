import importlib.util,json,re,subprocess,sys,tempfile,unittest
from decimal import Decimal
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(path,name):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
class PublicPackTests(unittest.TestCase):
 def test_skill_names_and_local_references_are_valid(self):
  for p in (ROOT/'skills').glob('*/SKILL.md'):
   s=p.read_text(encoding='utf8');name=re.search(r'^name: (.+)$',s,re.M)[1];self.assertEqual(name,p.parent.name)
   self.assertRegex(name,r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
   for link in re.findall(r'\]\(([^)]+)\)',s):
    if '://' not in link:self.assertTrue((p.parent/link).is_file(),link)
 def test_ad_sample_reproduces_metrics(self):
  base=ROOT/'skills/deepseen-ad-report-lite';m=load(base/'scripts/diagnose_ads.py','ads');table,sheet=m.load_table(base/'assets/sample-ads.csv');r=m.analyze(table,sheet,target_roas=Decimal('2.5'));self.assertEqual(r['groups'][0]['metrics']['roas'],Decimal('1.25'));self.assertEqual(r['groups'][0]['known_totals']['spend'],360)
 def test_ad_cli_runs_without_site_packages(self):
  base=ROOT/'skills/deepseen-ad-report-lite';p=subprocess.run([sys.executable,'-I','-S','-X','utf8',str(base/'scripts/diagnose_ads.py'),str(base/'assets/sample-ads.csv'),'--demo'],capture_output=True,encoding='utf8');self.assertEqual(p.returncode,0,p.stderr);self.assertIn('虚构示例',p.stdout)
 def test_quality_missing_binding_cannot_pass(self):
  m=load(ROOT/'skills/deepseen-asset-quality-audit/scripts/check_media_review.py','audit');r=m.check_review(dict(sha256='a'*64,videoTracks=1,audioTracks=1,durationSeconds=8,fullDecodePassed=True),{});self.assertEqual(r['status'],'unverified')
 def test_director_requires_actual_result_before_quality_claim(self):
  s=(ROOT/'skills/deepseen-commerce-director-lite/SKILL.md').read_text(encoding='utf8');self.assertIn('尚未生成',s);self.assertIn('导演自我评价', (ROOT/'README.md').read_text(encoding='utf8'))
if __name__=='__main__':unittest.main()
