# -*- coding: utf-8 -*-
import io,re,glob,json,sys

# ---------- 코퍼스 ----------
corpus=[]
for f in glob.glob('corpus/*.txt'):
    corpus.append(io.open(f,encoding='utf-8',errors='ignore').read())
C=re.sub(r'\s+','', '\n'.join(corpus))          # 공백 제거본
Cd=re.sub(r'[,\s]','', '\n'.join(corpus))       # 공백+콤마 제거본

def inC(tok):
    t=re.sub(r'\s+','',tok)
    if t in C: return True
    t2=re.sub(r'[,\s]','',tok)
    return t2 in Cd

# ---------- 문서 ----------
src=io.open(sys.argv[1],encoding='utf-8').read()
ENT=[('&ldquo;','"'),('&rdquo;','"'),('&lsquo;',"'"),('&rsquo;',"'"),('&amp;','&'),
     ('&sect;','§'),('&mdash;','—'),('&nbsp;',' '),('&rarr;','→'),('&times;','×'),
     ('&lt;','<'),('&gt;','>'),('&#9312;','①'),('&#9313;','②'),('&#9314;','③'),
     ('&#9315;','④'),('&#9316;','⑤'),('&#9317;','⑥'),('&#9318;','⑦'),('&#9319;','⑧'),
     ('&#9320;','⑨'),('&#9327;','⑬'),('&#9328;','⑭'),('&#9329;','⑮'),('&#9670;','◆'),('&#9675;','○')]
def plain(h):
    t=re.sub(r'<[^>]+>',' ',h)
    for a,b in ENT: t=t.replace(a,b)
    return re.sub(r'\s+',' ',t).strip()

# 전체 텍스트 단위 추출 (블록 누락 방지)
body = src[src.index('<body'):] if '<body' in src else src
body = re.sub(r'<style.*?</style>','',body,flags=re.S)
body = re.sub(r'<script.*?</script>','',body,flags=re.S)
# 태그를 개행으로 바꿔 문맥 보존
flat = plain(body)
# 문장 단위로 쪼개 문맥 제공
sents = re.split(r'(?<=[.!?\u3002])\s+|\s{2,}', flat)
blocks=[(0,x.strip()) for x in sents if len(x.strip())>2]

# ---------- 토큰 규칙 ----------
RULES=[
 ('전화', r'\b1[0-9]{3}-[0-9]{4}\b|\b1357\b|\b1332\b|\b1350\b|\b1397\b|\b129\b|\b182\b'),
 ('도메인', r'[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:or|go|co)\.kr'),
 ('업종코드', r'\b\d{5}\b'),
 ('금액', r'\b\d[\d,]*(?:\.\d+)?\s?(?:조|억원|억|천만원|만원|백만원)\b'),
 ('비율', r'\b\d+(?:\.\d+)?\s?%p?\b'),
 ('조문', r'§\s?\d+(?:조의\d+)?|제\s?\d+조(?:의\d+)?'),
 ('기간', r'\b\d+\s?(?:년|개월|영업일|일)\b'),
 ('점수', r'\b\d{3}\s?점\b'),
]
IGNORE_NUM={'2026','2025','2027','2024','1','2','3'}

rows=[]
for ln,txt in blocks:
    for kind,pat in RULES:
        for mm in re.finditer(pat, txt):
            tok=mm.group(0).strip()
            core=re.sub(r'[^\d]','',tok)
            if kind in ('기간','비율','점수') and core in IGNORE_NUM: continue
            ok=inC(tok)
            if not ok and kind=='조문':
                n=re.sub(r'[^\d조의]','',tok)
                m2=re.match(r'(\d+)(?:조의(\d+))?', re.sub(r'[^\d조의]','',tok).replace('조의','-'))
                num=re.findall(r'\d+', tok)
                if num:
                    cand=['제%s조'%num[0]]
                    if len(num)>1: cand.append('제%s조의%s'%(num[0],num[1]))
                    ok=any(inC(x) for x in cand)
            if not ok and kind=='도메인':
                import glob,os
                key=tok.split('.')[0].replace('www','')
                ok=any(key and key in os.path.basename(p) for p in glob.glob('corpus/web_*.txt'))
            if not ok and kind=='금액':
                ok=inC(core)          # 1조 7,558억 → 17558
            if not ok and kind in ('비율','기간','점수'):
                ok=inC(core+tok[-1])  # 숫자+단위
            rows.append({'line':ln,'kind':kind,'token':tok,'ok':ok,'ctx':txt[:150]})

io.open(sys.argv[2],'w',encoding='utf-8').write(json.dumps(rows,ensure_ascii=False,indent=1))
tot=len(rows); bad=sum(1 for r in rows if not r['ok'])
print('대조 토큰 %d개  /  원문 확인 %d  /  미확인 %d (%.0f%%)'%(tot,tot-bad,bad,100*bad/tot))
from collections import Counter
c=Counter((r['kind'], r['ok']) for r in rows)
for k,_ in RULES:
    o=c[(k,True)]; x=c[(k,False)]
    if o+x: print('  %-6s 확인 %3d / 미확인 %3d'%(k,o,x))
