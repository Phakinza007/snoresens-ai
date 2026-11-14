import sys,zipfile,re,shutil,os
src=sys.argv[1];tmp=src+'.tmp'
with zipfile.ZipFile(src) as zi,zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as zo:
    for item in zi.infolist():
        if item.filename.endswith('/'):continue
        data=zi.read(item.filename)
        if item.filename.startswith('ppt/theme/'):
            x=data.decode('utf8')
            x=x.replace('<a:cs typeface=""/>','<a:cs typeface="Tahoma"/>')
            x=re.sub(r'<a:font script="Thai" typeface="[^"]*"/>','<a:font script="Thai" typeface="Tahoma"/>',x)
            data=x.encode('utf8')
        zo.writestr(item,data)
shutil.move(tmp,src);print('fonts fixed')
