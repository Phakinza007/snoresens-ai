import json,sys
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
for f in ['/System/Library/Fonts/Supplemental/Tahoma.ttf','/System/Library/Fonts/Supplemental/Tahoma Bold.ttf']:fm.fontManager.addfont(f)
plt.rcParams.update({'font.family':'Tahoma','font.size':13,'axes.edgecolor':'#C9D2E3','axes.labelcolor':'#15233F','xtick.color':'#15233F','ytick.color':'#6B7A99'})
D=sys.argv[1];M=json.load(open(__import__('pathlib').Path(__file__).resolve().parents[3]/'results/model-comparison/metrics.json'))
NAVY,BLUE,AMBER,MUTED,ICE='#1B2E5A','#3157F5','#F2A93B','#8EA6D8','#DDE3EE'
def clean(ax):
    for s in ['top','right','left']:ax.spines[s].set_visible(False)
    ax.yaxis.grid(True,color=ICE,lw=.8);ax.set_axisbelow(True);ax.tick_params(axis='y',length=0)
# split chart
fig,ax=plt.subplots(figsize=(7.2,5.3),dpi=220)
cats=['Train','Validation','Test'];snore=[350,75,75];kag=[343,74,74];br=[32,12,14]
b1=ax.bar(cats,snore,color=BLUE,width=.55,label='กรน (1)')
b2=ax.bar(cats,kag,bottom=snore,color=MUTED,width=.55,label='ไม่กรน (0) · Kaggle')
b3=ax.bar(cats,br,bottom=[a+b for a,b in zip(snore,kag)],color=AMBER,width=.55,label='ไม่กรน (0) · หายใจ Coswara')
for bars,vals,bot,col in [(b1,snore,[0]*3,'white'),(b2,kag,snore,NAVY)]:
    for r,v,bo in zip(bars,vals,bot):ax.text(r.get_x()+r.get_width()/2,bo+v/2,str(v),ha='center',va='center',color=col,fontsize=12,fontweight='bold')
for r,v,a,b in zip(b3,br,snore,kag):ax.text(r.get_x()+r.get_width()+.04,a+b+v/2,f'+{v}',ha='left',va='center',color='#9A6410',fontsize=12,fontweight='bold')
for i,(a,b,c) in enumerate(zip(snore,kag,br)):ax.text(i,a+b+c+12,f'รวม {a+b+c}',ha='center',va='bottom',color=NAVY,fontsize=13,fontweight='bold')
clean(ax);ax.set_ylim(0,800);ax.set_title('งานกรน: จำนวนคลิปต่อชุด',color=NAVY,fontsize=15,fontweight='bold',loc='left',pad=12)
ax.legend(loc='upper right',frameon=False,fontsize=11);fig.tight_layout();fig.savefig(f'{D}/chart-split.png',transparent=False,facecolor='white')
# accuracy chart
order=['Logistic Regression','Random Forest','Decision Tree','SVM (RBF)','k-NN','Dense head v2 (web)']
lab=['Logistic\nReg. (ดีสุด)','Random\nForest','Decision\nTree','SVM\n(RBF)','k-NN','Dense v2\n(เว็บ)']
acc=[M['models'][k]['test']['accuracy']*100 for k in order];f1=[M['models'][k]['test']['f1']*100 for k in order]
fig,ax=plt.subplots(figsize=(8.2,5.3),dpi=220);import numpy as np;x=np.arange(len(order));w=.36
r1=ax.bar(x-w/2,acc,w,color=BLUE,label='Test accuracy');r2=ax.bar(x+w/2,f1,w,color=AMBER,label='F1 (กรน)')
for rs in (r1,r2):
    for r in rs:ax.text(r.get_x()+r.get_width()/2,r.get_height()+.12,f'{r.get_height():.1f}',ha='center',va='bottom',fontsize=10,color=NAVY)
ax.set_xticks(x,lab,fontsize=11);ax.set_ylim(90,101.6);ax.set_yticks(range(90,101,2));clean(ax)
ax.set_title('ชุดทดสอบ 149 คลิป (%) · แกนเริ่มที่ 90%',color=NAVY,fontsize=15,fontweight='bold',loc='left',pad=12)
ax.legend(loc='upper right',frameon=False,fontsize=11,ncol=2);fig.tight_layout();fig.savefig(f'{D}/chart-accuracy.png',facecolor='white')
print('charts ok')
