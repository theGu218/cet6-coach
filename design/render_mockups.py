from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(r"D:\codex\CET6Coach\design")
W, H = 1440, 900
BG = "#F4F6FB"; CARD = "#FFFFFF"; SIDE = "#172554"; ACTIVE = "#2E4A8D"
PRIMARY = "#3157C8"; TEXT = "#172033"; MUTED = "#667085"; BORDER = "#DFE4EF"
GREEN = "#16865B"; PALE_GREEN = "#EAF7F1"; RED = "#C43D4B"; PALE_RED = "#FCEFF1"
FONT = r"C:\Windows\Fonts\msyh.ttc"; BOLD = r"C:\Windows\Fonts\msyhbd.ttc"; LATIN = r"C:\Windows\Fonts\segoeui.ttf"

def f(size, bold=False): return ImageFont.truetype(BOLD if bold else FONT, size)
def txt(d, xy, s, size=18, color=TEXT, bold=False): d.text(xy, s, font=f(size,bold), fill=color, anchor="lt")
def latin(d, xy, s, size=18, color=MUTED): d.text(xy, s, font=ImageFont.truetype(LATIN,size), fill=color, anchor="lt")
def box(d, rect, fill=CARD, outline=BORDER, radius=14, width=1): d.rounded_rectangle(rect, radius=radius, fill=fill, outline=outline, width=width)
def button(d, rect, label, primary=True, color=None):
    fill = color or (PRIMARY if primary else CARD)
    box(d, rect, fill, None if primary else BORDER, 9)
    x1,y1,x2,y2=rect
    txt(d, ((x1+x2)//2 - len(label)*9, y1+12), label, 16, "white" if primary else TEXT, primary)
def sidebar(d, active):
    d.rectangle((0,0,256,H), fill=SIDE)
    txt(d,(28,30),"CET—6",36,"white",True)
    txt(d,(28,83),"六级冲刺 · 学习工作台",15,"#C4D2F4")
    items=["今日复习","核心词汇","真题阅读","积累本","写作训练","翻译训练","复盘统计","设置与数据"]
    y=150
    for item in items:
        if item==active: box(d,(16,y-8,240,y+46),ACTIVE,None,9)
        d.ellipse((32,y+8,40,y+16), fill="#AFC1EF" if item!=active else "white")
        txt(d,(56,y),item,18,"white" if item==active else "#DCE4FA",item==active)
        y+=66
    box(d,(16,748,240,856),"#101D42",None,12)
    txt(d,(32,766),"今日已学习 35 分钟",15,"#C4D2F4")
    txt(d,(32,798),"连续学习 6 天",22,"white",True)
    txt(d,(32,830),"先复习，再学新内容",13,"#AFC1EF")
def base(active):
    im=Image.new("RGB",(W,H),BG); d=ImageDraw.Draw(im); sidebar(d,active); return im,d

def home():
    im,d=base("今日复习")
    txt(d,(292,34),"今天，先完成最重要的复习",30,TEXT,True)
    txt(d,(292,80),"2026年11月2日 · 预计 75 分钟 · 到期复习优先",16,MUTED)
    button(d,(1216,38,1398,86),"继续复习")
    box(d,(284,120,1408,246),"#EAF0FF","#CDD9F7")
    txt(d,(312,142),"今日建议",15,PRIMARY,True)
    txt(d,(312,174),"先复习 18 个到期词，再开始今天的新内容",24,TEXT,True)
    txt(d,(312,213),"错词不会因本轮答对就直接消失，后续仍会安排复查。",15,MUTED)
    stats=[("到期复习","18 词","优先完成"),("今日新词","12 / 20","还剩 8 词"),("阅读正确率","68%","最近 5 次练习")]
    x=284
    for title,value,note in stats:
        box(d,(x,266,x+360,382)); txt(d,(x+22,284),title,15,MUTED)
        txt(d,(x+22,313),value,28,PRIMARY,True); txt(d,(x+22,352),note,13,MUTED); x+=382
    box(d,(284,404,1040,858)); txt(d,(310,426),"今日复习清单",22,TEXT,True)
    txt(d,(310,462),"按优先级排列，完成后自动进入下一项",14,MUTED)
    tasks=[("1","旧词与错词复习","18 词 · 约 15 分钟","开始",True),
           ("2","新词学习与四选一检测","今日 12/20 · 英译汉阶段","继续",False),
           ("3","真题仔细阅读","2023年6月 · 第1套 · 学习模式","开始",False),
           ("4","积累本复习","8 条句式与主题表达 · 约 10 分钟","查看",False)]
    y=502
    for num,title,note,label,hot in tasks:
        box(d,(306,y,1018,y+70),"#F7F9FD" if not hot else "#EEF3FF",None,10)
        d.ellipse((322,y+17,358,y+53),fill=PRIMARY if hot else "#D7E0F5")
        txt(d,(334,y+22),num,16,"white" if hot else PRIMARY,True)
        txt(d,(376,y+12),title,17,TEXT,True); txt(d,(376,y+40),note,13,MUTED)
        button(d,(910,y+15,996,y+55),label,hot)
        y+=82
    box(d,(1062,404,1408,624)); txt(d,(1086,426),"复习顺序",20,TEXT,True)
    steps=[("01","到期旧词与错词"),("02","新词和阶段检测"),("03","真题阅读与复盘"),("04","表达积累（可选）")]
    y=468
    for num,label in steps:
        txt(d,(1088,y),num,14,PRIMARY,True); txt(d,(1130,y-2),label,15,TEXT); y+=38
    box(d,(1062,646,1408,858)); txt(d,(1086,666),"本周学习",20,TEXT,True)
    vals=[35,55,40,70,50,80,35]
    for i,v in enumerate(vals):
        x=1090+i*42; top=818-int(v*1.25)
        d.rounded_rectangle((x,top,x+22,818),radius=5,fill=PRIMARY if i==6 else "#B7C7EF")
        txt(d,(x+2,830),"一二三四五六日"[i],13,MUTED)
    im.save(OUT/"首页效果图.png")

def vocab():
    im,d=base("核心词汇")
    txt(d,(292,34),"核心词汇",30,TEXT,True)
    txt(d,(292,80),"今日复习 18 词 · 新学 12/20 · 先检测，再安排下一次复习",16,MUTED)
    tabs=[("今日学习",False),("四选一检测",True),("错词本",False),("生词本",False),("词汇表",False)]
    x=284
    for label,active in tabs:
        box(d,(x,116,x+184,164),CARD if active else "#E9EDF5",None,9)
        txt(d,(x+22,130),label,16,PRIMARY if active else MUTED,active); x+=194
    box(d,(284,186,1038,858)); txt(d,(312,210),"英译汉 · 第 6 / 20 题",15,PRIMARY,True)
    txt(d,(868,210),"本轮答错 2 词",14,MUTED)
    d.rounded_rectangle((312,250,1010,258),radius=4,fill="#E3E8F1")
    d.rounded_rectangle((312,250,521,258),radius=4,fill=PRIMARY)
    txt(d,(448,292),"controversy",38,TEXT,True)
    latin(d,(463,347),"/ˈkɒntrəvɜːsi/  n.",18,MUTED)
    txt(d,(312,398),"请选择最准确的中文释义",17,TEXT,True)
    options=[("A","争议；争论",GREEN,PALE_GREEN,"正确答案"),
             ("B","传统；惯例",TEXT,CARD,""),
             ("C","共识；一致意见",RED,PALE_RED,"你的选择"),
             ("D","结果；后果",TEXT,CARD,"")]
    y=440
    for letter,meaning,color,fill,note in options:
        box(d,(312,y,1010,y+64),fill,color if note else BORDER,10,2 if note else 1)
        txt(d,(332,y+16),letter,18,color,True); txt(d,(382,y+15),meaning,18,color,bool(note))
        if note: txt(d,(836,y+19),note,14,color,True)
        y+=76
    box(d,(312,754,1010,820),"#FFF7E9",None,10)
    txt(d,(332,770),"已加入错词本 · 本轮稍后会再次出现，明天还会复查",16,"#8A5208",True)
    button(d,(820,830,1010,872),"下一题")
    box(d,(1060,186,1408,470)); txt(d,(1084,210),"三阶段检测",20,TEXT,True)
    stages=[("1","英译汉","当前阶段",True),("2","汉译英","复习时逐步解锁",False),("3","语境选择","检验实际理解",False)]
    y=260
    for num,title,note,current in stages:
        d.ellipse((1086,y,1122,y+36),fill=PRIMARY if current else "#D7E0F5")
        txt(d,(1098,y+7),num,15,"white" if current else PRIMARY,True)
        txt(d,(1140,y-2),title,17,TEXT,True); txt(d,(1140,y+24),note,13,MUTED); y+=66
    box(d,(1060,492,1408,684)); txt(d,(1084,514),"错词怎么处理？",20,TEXT,True)
    notes=["① 自动进入错词本","② 本轮稍后重新出现","③ 本轮结束后集中重练","④ 间隔几天后再次检测"]
    y=558
    for note in notes: txt(d,(1086,y),note,15,MUTED); y+=30
    box(d,(1060,706,1408,858),"#EAF0FF","#CDD9F7")
    txt(d,(1084,728),"掌握不靠“点认识”",19,PRIMARY,True)
    txt(d,(1084,768),"跨日期通过多次检测，",15,TEXT)
    txt(d,(1084,796),"并完成语境题，才标记掌握。",15,TEXT)
    im.save(OUT/"词汇检测效果图.png")

if __name__ == "__main__":
    home(); vocab(); print("mockups created")

