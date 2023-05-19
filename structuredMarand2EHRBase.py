import json
import logging,argparse
from flatten_json import flatten
import re


def get_composition_name(cM):
    '''retrieve the name of the composition (template)'''
    for child in cM:
        if child != 'ctx':
            cname=child
            return cname


def convert_ctx(cM,cE):
    '''convert the ctx from a Marand composition to the equivalent in EHRBase'''
    if 'ctx' not in cM:
        logging.warning('ctx not in Marand Composition')
        return
    cctx=cM['ctx']
    if 'language' in cctx:
        cE['language']=[{
            '|code':cctx['language'],
            '|terminology':'ISO_639-1'}]
    else:#defaults to english
        cE['language']=[{
            '|code':'en',
            '|terminology':'ISO_639-1'}]
                
    if 'territory' in cctx:
        if cctx['territory']=='en':
            cctx['territory']='GB'
        cE['territory']=[{
            '|code':cctx['territory'],
            '|terminology':'ISO_3166-1'}]    
    else:#defaults to IT
        cE['territory']=[{
            '|code':'IT',
            '|terminology':'ISO_3166-1'}] 
    cE['composer']=[{
        '|name':cctx['composer_name']
    }]

def convert_context(cM,cname):
    '''convert the context from a Marand composition to the equivalent in EHRBase'''
    cctx=cM[cname][0]['context'][0]
    cont={}
    if 'setting' in cctx:
        if cctx['setting'][0]['|code']=='setting code':#defaults to other care if not set
            cctx['setting'][0]['|code']='238'
            cctx['setting'][0]['|value']='other care'

    for k in cctx:
        if k=='setting':
           cont['setting']=[{ 
               '|code':cctx['setting'][0]['|code'],
               '|value':cctx['setting'][0]['|value'],
               '|terminology':'openehr'
           }] 
        else:
            cont[k]=cctx[k]
    return cont

def convert_category(cM,cE,cname):
    '''convert the category entry from a Marand composition to the equivalent in EHRBase'''
    cctx=cM[cname][0]['category'][0]
    if cctx['|code']=='433':
        cE['category']=[{
            '|code':cctx['|code'],
            '|terminology':'openehr',
            '|value':'event'
        }]
    else:
        logging.warning(f"category not event category_code={cctx['|code']}\nPlease add category manually")
    
def convert_content(cM,cE,cname):
    '''convert the rest of the content from Marand to EHRBase'''
    cctx=cM[cname][0]
    for k in cctx:
        if k not in cE:
            cE[k]=cctx[k]

def wtinfoaddtoList(mylist,elements,rmtypeobj,compulsory=False):
    for el in elements:
        eid=el['id']
        aqlpath=el['aqlPath']
        rmtype=el['rmType']
        if 'content' in aqlpath and rmtype==rmtypeobj:
            if 'inputs' in el:
                inputs=el['inputs']
            else:
                inputs=[]
            if compulsory:
                if el['min']>0:
                    mylist.append([eid,aqlpath,rmtype,inputs])
            else:
                mylist.append([eid,aqlpath,rmtype,inputs])
        if 'children' in el:
            wtinfoaddtoList(mylist,el['children'],rmtypeobj,compulsory)
    return mylist


def etinfoaddtoListDVCODEDTEXT(extemp):
    mylist2=[]
    for k in extemp:
        if k.endswith('|code') and not k.endswith('math_function|code') and \
        not k.endswith('/category|code') and not k.endswith('context/setting|code') and \
        not ':1' in k and not ':2' in k and not ':3' in k:
            if k[:-4]+'value' in extemp and k[:-4]+'terminology' in extemp:
                path=k[:-5]
                el={}
                lastslash=path.rfind('/')
                id=path[lastslash+1:]
                if id[-2]==':':
                    id=id[:-2]
                el['id']=id
                el['code']=extemp[k]
                el['value']=extemp[k[:-4]+'value']
                el['terminology']=extemp[k[:-4]+'terminology']
                sel={}
                sel[path]=el
                mylist2.append(sel)
    return mylist2

def comparelists_WT_ET_DVCODEDTEXT(mylistW,mylistE):
    '''compare and merge the lists of dv_coded_text elements made from webtemplate and example composition from template
    output: list with id,possiblevalues,[match_indicator,pathfromExample]'''
    newlist=[]
    for w in mylistW:
        idw=w[0]
        pw=w[1]
        nvalues=len(w[3][0]['list'])
        values=[{'code':w[3][0]['list'][i]['value'],'value':w[3][0]['list'][i]['label'],
                 'terminology':w[3][0]['terminology']} for i in range(nvalues)]
        if len(w[3])>1:
            if 'suffix' in w[3][1]:
                values.append({w[3][1]['suffix']:'othertext'})
        pathelements=[]
        if 'name/value' in pw:
            ifind=0
            while ifind != -1:
                ifindold=ifind
                ifind=pw.find('name/value=',ifindold+1)
                if ifind != -1:
                    jfind=pw.find("'",ifind+12)
                    pathelements.append(pw[ifind+12:jfind].lower().replace(' ','_'))
        liste=[]
        for e in mylistE:
            for k in e:
                pe=k
                ide=e[k]['id']
                g=0
                if idw==ide:
                    logging.debug('--------')
                    logging.debug(f'id={ide}')
                    logging.debug(f'pathW={pw}')
                    logging.debug(f'pathE={pe}')
                    if len(pathelements)>0:
                        for p in pathelements:
                            if p in pe:
                                g+=1
                    liste.append([g,pe])
        newlist.append([idw,values,liste])
    #logging.debug('new list start')
    #for n in newlist:
    #    logging.debug(n[0],n[2][0][1])
    #logging.debug('newlist end')
    final_list=[]
    for n in newlist:
        if len(n[2])>1:
            wl=max(n[2], key = lambda i : i[0])
            final_list.append([n[0],n[1],[wl]])
        else:
            final_list.append(n)
    #logging.debug(f'newlist={newlist}')
    #logging.debug(f'final_list={final_list}')
    #for f in final_list:
    #    logging.debug(f[0],f[2][0][1])
    #logging.debug('********')
    return final_list

def flattenpath(cM):
    cMstring=json.dumps(cM)
    cM22string=cMstring.replace("_","@")
    cM2=json.loads(cM22string)
    return flatten(cM2)

    
def createpathstructured(pathflat):
    '''convert a flat path to a structured one and return it along with a list of elements to be checked for occurrences in composition
    Return strings so it needs eval on the calling subroutine'''
    pathsplit=pathflat.split('/')
    newpathsplit=[]
    lenocc=[]
    for i,p in enumerate(pathsplit):
        if p.endswith(':0'):
            p2=p[:-2]
            newpathsplit.append("['"+p2+"']")             
            if i != len(pathsplit)-1:
                pstruct='[0]'.join(newpathsplit)
                logging.debug(f'pstruct={pstruct}')
                lenocc.append(pstruct)    
        else:
            newpathsplit.append("['"+p+"']")
    pathstruct='[0]'.join(newpathsplit)
    
    return (pathstruct,lenocc)

def flatlike(l):
    l2=l.replace('_','@')
    l3=re.sub(r"\[\'(\D*)\'\]",r"\g<1>",l2,re.MULTILINE)
    l4=re.sub(r"\[(\d)\]",r"_\g<1>_",l3,re.MULTILINE)
    return l4

def structlikefromflat(l):
    l2=re.sub(r"\_(\d)\_","'][\g<1>]['",l)
    l3=re.sub(r"\_(\d)$","'][\g<1>]",l2)
    l4=l3.replace('@','_')
    l5="['"+l4
    return l5

def createnewpaths(path,lenocc,flattenedcm,cname):

    if len(lenocc)==0:
        lcname2=len(cname)+7#len=2{['}+len(cname)+2{']}+3{[0]}'
        newpaths=[path[lcname2:]]
    else:
        newpaths_partials=[]
        for l in lenocc:
            newpaths_partials_lenocc=[]
            pathtocheck=flatlike(l)
            occurrence_exists=True
            i=-1
            while occurrence_exists:
                i=i+1
                p=pathtocheck+'_'+str(i)
                found=False
                for f in flattenedcm:
                    if f.startswith(p):
                        logging.debug(f'{p} found in {f}')
                        newpaths_partials_lenocc.append(p)
                        found=True
                        break
                occurrence_exists=found
            newpaths_partials.append(newpaths_partials_lenocc)
        
        logging.debug('NPP')
        logging.debug(newpaths_partials)

        newpathtotgarbled=getpaths(newpaths_partials)
        logging.debug('NPG')
        logging.debug(newpathtotgarbled)

        newpaths=[]
        lcname2=len(cname)+7#len=2{['}+len(cname)+2{']}+3{[0]}'
        logging.debug('PIECE')
        lastnpg=structlikefromflat(newpathtotgarbled[-1])
        lastpiecepath=path[len(lastnpg):]
        logging.debug(f'path={path}')
        logging.debug(f'lastnpg={lastnpg}')
        for npg in newpathtotgarbled:
            logging.debug(f'npg={npg}')
            npgn=structlikefromflat(npg)
            logging.debug(f'npgn={npgn}')
            newpaths.append(npgn[lcname2:]+lastpiecepath)
            logging.debug(f'npfinal={npgn[lcname2:]+lastpiecepath}')

        logging.debug('CREATENEWPATHS')
        logging.debug(f'path={path}')
        logging.debug(f'newpaths={newpaths}')

    return newpaths

def getpaths(newpaths_partials):
    oldfirst=newpaths_partials[0][0]
    for i in range(1,len(newpaths_partials)):
        first=newpaths_partials[i][0]
        if not first.startswith(oldfirst):
            print(f'Error: inner path {oldfirst} not included in outer one {first}')
            break
        oldfirst=first

    newpath=[]
    if len(newpaths_partials)==1:
        i=0
        for j,n in enumerate(newpaths_partials[i]):
            newpath.append(n)

    else:
        i=0
        for j,n in enumerate(newpaths_partials[i]):
            logging.debug(f'j={j}')
            piece=[n]
            for m in range(i+1,len(newpaths_partials)):
                logging.debug(f'm={m}')
                for k,nn in enumerate(newpaths_partials[m]):
                    if k==0:
                        newpiece=[]
                    logging.debug(f'nn={nn}')
                    for p in piece:
                        newpiece.append(p+nn[len(p):])

                    logging.debug(f'newpieces {newpiece}')
                    
                    if k==len(newpaths_partials[m])-1:
                        piece=newpiece
                    if m==len(newpaths_partials)-1 and k==len(newpaths_partials[m])-1:
                        # logging.debug(f'NP: newpiece={newpiece}')
                        newpath.extend(newpiece)
    
    logging.debug(f'len(newpath)={len(newpath)}')

    return newpath



def findpathtocoded(cE,listofcoded,cname,flattenedcm):
    ''' find path in Marand for dv_coded_text elements in list of paths and return it together with allowed values'''
    pathtocoded=[]
    for lc in listofcoded:
        logging.debug(f'id={lc[0]}')
        (path,lenocc)=createpathstructured(lc[2][0][1])
        logging.debug('FINDPATHTOCODED')
        for l in lenocc:
            logging.debug(flatlike(l))
        #logging.debug(path)
        #logging.debug(lenocc)
        #path=path[lcname:]#remove template name
        logging.debug(f'path={path} lenocc={lenocc}')
        #logging.debug(f'path[lcname:]={path[lcname:]}')
        newpaths=createnewpaths(path,lenocc,flattenedcm,cname)
        #logging.debug(path)
        #logging.debug(eval("cE"+path))
        #pathtocoded.append(["cE"+path,lc[1]])
        #logging.debug(f'appended [{"cE"+path} , {lc[1]}]')

        if len(newpaths)!=0:
            for p in newpaths:
                pathtocoded.append(["cE"+p,lc[1]])
                logging.debug(f'appended [{"cE"+p} , {lc[1]}]')

        # if len(lenocc)==0:
        #     pass
        # elif len(lenocc)>1:
        #     logging.debug('More than one possible occurrence in the same path. Not yet implemented')
        #     logging.debug(lenocc)
        # else:
        #     logging.debug('LENOCC=1')
        #     o=lenocc[0][lcname:]
        #     logging.debug(f'o={o}')
        #     l=eval("len(cE"+o+")")
        #     logging.debug(f'len(cE+o)={l}')
        #     ll=len(o)
        #     logging.debug(f'll={ll}')
        #     basepath1="cE"+path[:ll]
        #     logging.debug(f'basepath1={basepath1}')
        #     basepath2=path[ll+3:]
        #     logging.debug(f'basepath2={basepath2}')
        #     for i in range(2,l+1):
        #         occpath=basepath1+'['+str(i-1)+']'+basepath2
        #         logging.debug(f'occpath={occpath}')
        #         logging.debug(f'lc[1]={lc[1]}')
        #         pathtocoded.append([occpath,lc[1]])
        
    return pathtocoded



def fixes_dv_coded_text(cE,webtemp,extemp,cname,flattenedcm):
    #find all dv_coded_text in webtemplate content
    wt=webtemp['webTemplate']['tree']['children']
    mylistW=[]
    mylistW=wtinfoaddtoList(mylistW,wt,'DV_CODED_TEXT')
    #logging.debug(len(mylistW))
    #logging.debug(mylist)
    #create same list but from example composition
    mylistE=etinfoaddtoListDVCODEDTEXT(extemp)
    #logging.debug(json.dumps(mylistE,indent=2))
    #logging.debug(len(mylistE))

    #compare and merge the two lists to find the right paths and allowed values
    listofcoded=comparelists_WT_ET_DVCODEDTEXT(mylistW,mylistE)

    #find path in Marand for the dv coded values
    pathtocoded=findpathtocoded(cE,listofcoded,cname,flattenedcm)
    #logging.debug(json.dumps(pathtocoded,indent=2))

    logging.debug('------')
    #fix all the coded_text in the list
    #code is right, the rest must be corrected
    for p in pathtocoded:
        logging.debug('&&&&&&&&&&&&loop in pathtocoded&&&&&&&&&&&&&&&&&')
        logging.debug(p[0])
        logging.debug(p[1])
        logging.debug(eval(p[0]))
        cpresent=eval(p[0])[0]
        if '|code' in cpresent:
            otherpresent=cpresent.pop('|other', None)
            if otherpresent != None:
                logging.debug('removed other')
            codepresent=cpresent['|code']
            valuepresent='Not found'
            logging.debug(f'code={codepresent}')
            for cv in p[1]:
                if 'code' in cv:
                    if cv['code']==codepresent:
                        valuepresent=cv['value']
                        logging.debug(f'=>value={valuepresent}')
                        cpresent['|value']=valuepresent
                        logging.debug(eval(p[0])[0]['|value'])
                        if 'terminology' in cv:
                            cpresent['|terminology']=cv['terminology']
                            logging.debug(f"=>{eval(p[0])[0]['|terminology']}")
                        break
        elif '|other' in cpresent:
            logging.debug('other present')
            if 'other' in p[1][-1]:
                logging.debug('other admissible')
                pass#do nothing
            else:
                logging.warning(f'other not allowed for {p[0]}')

def etinfoaddtoListDVQUANTITY(extemp):
    mylist2=[]
    for k in extemp:
        if k.endswith('|unit'):
            if k[:-4]+'magnitude' in extemp and \
                not ':1' in k and not ':2' in k and not ':3' in k:
                path=k[:-5]
                el={}
                lastslash=path.rfind('/')
                id=path[lastslash+1:]
                if id[-2]==':':
                    id=id[:-2]
                el['id']=id
                el['magnitude']=extemp[k[:-4]+'magnitude']
                sel={}
                sel[path]=el
                mylist2.append(sel)
    return mylist2

def findpathtoquantity(cE,listofq,cname,flattenedcm):
    ''' find path in Marand for quantity elements in list of paths and return it'''
    # with open('pippo','w') as p:
    #     json.dump(cE,p)
    #logging.debug(json_list_traverse(cE))
    pathtoq=[]
    for lc in listofq:
        pathq=list(lc.keys())
        logging.debug(f"id={lc[pathq[0]]['id']}")
        (path,lenocc)=createpathstructured(pathq[0])
        logging.debug('FPQ')
        logging.debug(path)
        logging.debug(lenocc)
        #path=path[lcname:]#remove template name
        #logging.debug(path)
        #logging.debug(eval("cE"+path))
        newpaths=createnewpaths(path,lenocc,flattenedcm,cname)
        # pathtoq.append(["cE"+path])
        # if len(lenocc)==0:
        #     pass
        # elif len(lenocc)>1:
        #     logging.debug('More than one possible occurrence in the same path. Not yet implemented')
        #     logging.debug(lenocc)
        # else:
        #     o=lenocc[0][lcname:]
        #     logging.debug(o)
        #     l=eval("len(cE"+o+")")
        #     logging.debug(f'len={l}')
        #     ll=len(o)
        #     basepath1="cE"+path[:ll]
        #     basepath2=path[ll+3:]
        #     for i in range(2,l+1):
        #         occpath=basepath1+'['+str(i-1)+']'+basepath2
        #         logging.debug(occpath)
        #         pathtoq.append([occpath])
        if len(newpaths)!=0:
            for p in newpaths:
                pathtoq.append(["cE"+p])
                logging.debug(f'appended [{"cE"+p}]')

    return pathtoq

def fixes_dv_quantity(cE,webtemp,extemp,cname,flattenedcm):
    #find all dv_quantity in webtemplate content
    wt=webtemp['webTemplate']['tree']['children']
    mylistW=[]
    mylistW=wtinfoaddtoList(mylistW,wt,'DV_QUANTITY')
    #logging.debug(len(mylistW))
    #logging.debug(mylist)
    #create same list but from example composition
    mylistE=etinfoaddtoListDVQUANTITY(extemp)
    if len(mylistW) != len(mylistE):
        logging.debug(f'warning DV_QUANTITY: from template #entity={len(mylistW)} from composition #entity={len(mylistE)}')
    logging.debug(json.dumps(mylistE,indent=2))
    #logging.debug(len(mylistE))

    #compare and merge the two lists to find the right paths and allowed values
    #listofcoded=comparelists_WT_ET(mylistW,mylistE)

    #find path in Marand for the dv coded values
    pathtoq=findpathtoquantity(cE,mylistE,cname,flattenedcm)
    logging.debug(json.dumps(pathtoq,indent=2))

    logging.debug('------')
    #fix all the dv_quantity in the list
    #unit is right, missing magnitude
    for p in pathtoq:
        logging.debug('&&&&&&&&&&&&&&&&&&&&&&&&&&&&&')
        logging.debug(p[0])
        logging.debug(eval(p[0]))
        cpresent=eval(p[0])[0]
        if '|unit' in cpresent:
            if '|magnitude' not in cpresent:
                cpresent['|magnitude']=0
                logging.debug(cpresent)

def etinfoaddtoListDVPROPORTION(extemp):
    mylist2=[]
    for k in extemp:
        if k.endswith('|denominator'):
            logging.debug(f'k={k}**************')
            if k[:-11]+'numerator' in extemp and \
                not ':1' in k and not ':2' in k and not ':3' in k:
                path=k[:-12]
                el={}
                lastslash=path.rfind('/')
                id=path[lastslash+1:]
                if id[-2]==':':
                    id=id[:-2]
                el['id']=id
                el['numerator']=extemp[k[:-11]+'numerator']
                el['denominator']=extemp[k[:-11]+'denominator']
                sel={}
                sel[path]=el
                mylist2.append(sel)
    return mylist2

def findpathtoproportion(cE,listofp,cname,flattenedcm):
    ''' find path in Marand for proportion elements in list of paths and return it'''
    return findpathtoquantity(cE,listofp,cname,flattenedcm)


def fixes_dv_proportion(cE,webtemp,extemp,cname,flattenedcm):
    #find all dv_proportion in webtemplate content
    wt=webtemp['webTemplate']['tree']['children']
    mylistW=[]
    mylistW=wtinfoaddtoList(mylistW,wt,'DV_PROPORTION')
    #logging.debug(len(mylistW))
    #logging.debug(mylist)
    #create same list but from example composition
    mylistE=etinfoaddtoListDVPROPORTION(extemp)
    if len(mylistW) != len(mylistE):
        logging.debug(f'warning DV_PROPORTION: from template #entity={len(mylistW)} from composition #entity={len(mylistE)}')
    logging.debug(json.dumps(mylistE,indent=2))
    #logging.debug(len(mylistE))

    #compare and merge the two lists to find the right paths and allowed values
    #listofcoded=comparelists_WT_ET(mylistW,mylistE)

    #find path in Marand for the dv coded values
    pathtop=findpathtoproportion(cE,mylistE,cname,flattenedcm)
    logging.debug(json.dumps(pathtop,indent=2))

    logging.debug('------')
    #fix all the dv_proportion in the list
    #unit is right, missing magnitude
    for p in pathtop:
        logging.debug('&&&&&&&&&&&&&&&&&&&&&&&&&&&&&')
        logging.debug(p[0])
        logging.debug(eval(p[0]))
        cpresent=eval(p[0])[0]
        if '|denominator' in cpresent:
            if '|type' not in cpresent:
                cpresent['|type']=3
                if cpresent['|denominator'] != 0:
                    cpresent['']=cpresent['|numerator']/cpresent['|denominator']
                logging.debug(cpresent)

def readwt(wtfile):
    '''read EHRBase webtemplate file'''
    with open(wtfile) as wt:
        webtemp=json.load(wt)
    return webtemp


def readet(excomp):
    '''read EHRBase example file from template'''
    with open(excomp) as et:
        extemp=json.load(et)
    return extemp    

def findentriesinex(extemp,entries):
    mylist2=[]
    for e in entries:
        found=False
        for k in extemp:
            if  not found:
                ksplit=k.split('/')
                if e in ksplit and not ':1' in k and not ':2' in k and not ':3' in k:
                    logging.debug(f'k={k}**************')
                    kindex=ksplit.index(e)
                    kpath='/'.join(ksplit[:kindex+1])
                    logging.debug(kpath)
                    path=kpath
                    el={}
                    lastslash=path.rfind('/')
                    id=path[lastslash+1:]
                    if id[-2]==':':
                        id=id[:-2]
                    el['id']=id
                    sel={}
                    sel[path]=el
                    mylist2.append(sel)
                    found=True
    return mylist2    


def add_language_encoding(cE,webtemp,extemp,cname,flattenedcm):
    #find observation,action,evaluation,admin_entry in wt
    entries=[]
    wt=webtemp['webTemplate']['tree']['children']
    mylistW=[]
    mylistW=wtinfoaddtoList(mylistW,wt,'OBSERVATION')
    logging.debug(mylistW)
    for m in mylistW:
        entries.append(m[0])
    mylistW=[]
    mylistW=wtinfoaddtoList(mylistW,wt,'ACTION')
    logging.debug(mylistW)
    for m in mylistW:
        entries.append(m[0])
    mylistW=[]
    mylistW=wtinfoaddtoList(mylistW,wt,'EVALUATION')
    logging.debug(mylistW)
    for m in mylistW:
        entries.append(m[0])
    mylistW=[]
    mylistW=wtinfoaddtoList(mylistW,wt,'ADMIN_ENTRY')
    logging.debug(mylistW)
    for m in mylistW:
        entries.append(m[0])
    logging.debug(entries)
    #logging.debug(len(mylistW))

    #find entries in example composition
    mypathE=findentriesinex(extemp,entries)
    logging.debug(';;;;;;;;;;;;;;;;;;;;')
    logging.debug(mypathE)

    pathtoe=findpathtoproportion(cE,mypathE,cname,flattenedcm)
    #logging.debug(json.dumps(pathtoe,indent=2))
    for p in pathtoe:
            logging.debug('&&&&&&&&&&&&&&&&&&&&&&&&&&&&&')
            logging.debug(p[0])
            #logging.debug(eval(p[0]))
            cpresent=eval(p[0])
            for c in cpresent:
                if 'language' not in c:
                    c['language']= [
                                {
                                    "|code": "en",
                                    "|terminology": "ISO_639-1"
                                }
                            ]
                if 'encoding' not in c:
                    c['encoding']= [
                        {
                            "|code": "UTF-8",
                            "|terminology": "IANA_character-sets"
                        }
                    ]

def etinfoaddtoListcustom(extemp,customend):
    mylist2=[]
    for k in extemp:
        for c in customend:
            if k.endswith(c):
                if not ':1' in k and not ':2' in k and not ':3' in k:
                    path=k
                    el={}
                    lastslash=path.rfind('/')
                    id=path[lastslash+1:]
                    if id[-2]==':':
                        id=id[:-2]
                    el['id']=id
                    sel={}
                    sel[path]=el
                    mylist2.append(sel)
    return mylist2

def fix_position_substituted(cE,extemp,cname,flattenedcm):
    mypathps=etinfoaddtoListcustom(extemp,['position_substituted'])
    logging.debug(mypathps)
    pathtos=findpathtoproportion(cE,mypathps,cname,flattenedcm)

    for p in pathtos:
        logging.debug('&&&&&&&&&&&&&&&&&&&&&&&&&&&&&')
        logging.debug(p[0])
        logging.debug(p[0][:-24])
        logging.debug(eval("len('+p[0][:-24]+')"))
        cpresent=eval(p[0][:-24])
        cpresent['position_substituted']=[0]
        logging.debug(cpresent)
        #logging.debug(eval(p[0]))   
  
def fixes_dv_count(cE,webtemp,extemp,cname,flattenedcm):
    #find all dv_count in webtemplate content with min>0
    wt=webtemp['webTemplate']['tree']['children']
    mylistW=[]
    mylistW=wtinfoaddtoList(mylistW,wt,'DV_COUNT',True)
    #logging.debug(len(mylistW))
    logging.debug('555555555555555')
    logging.debug(mylistW)
    mylistfirsts=[m[0] for m in mylistW]
    mypathps=etinfoaddtoListcustom(extemp,mylistfirsts)
    logging.debug(mypathps)
    pathtos=findpathtoproportion(cE,mypathps,cname,flattenedcm)
    logging.debug(pathtos)
    logging.debug(type(pathtos))
    
    #fix all the min>1 dv_count  in the list
    for p in pathtos:
        logging.debug(p[0])
        i=p[0].rfind('[0]')+3
        logging.debug('&&&&&&&&&&&&&&&&&&&&&&&&&&&&&')
        logging.debug(p[0][:i])
        logging.debug(eval("len('+p[0][:i]+')"))
        cpresent=eval(p[0][:i])
        #logging.debug(cpresent)
        id=p[0][i+2:-2]
        logging.debug(id)
        cpresent[id]=[0]
        logging.debug(cpresent)
        #logging.debug(eval(p[0]))   

def readcomp(inputfile):
    with open(inputfile) as snv:
        compMARAND=json.load(snv)
    return compMARAND

def writecomp(outputfile,compEHRBase):
    with open(outputfile,'w') as snvout:
        json.dump(compEHRBase,snvout)


def main():
    '''convert a structured Marand composition to a EHRBase one
    input: composition returned from Marand Designer, template in webtemplate format
    output: composition in EHRBase structured format'''

    parser = argparse.ArgumentParser()
    parser.add_argument('--loglevel',help='the logging level:DEBUG,INFO,WARNING,ERROR or CRITICAL',default='WARNING')
    parser.add_argument('--inputfile',help='composition in structured format returned by Designer',default='snv_report_MINE.json')
    parser.add_argument('--inputwebtemplate',help='webtemplate from EHRBase',default='svn_webtemplate_EHRBASE.json')
    parser.add_argument('--inputexfile',help='example composition in flat format from EHRBase',default='svn_report_composition_exampleflat.json')
    parser.add_argument('--outputfile',help='composition in structured format for EHRBase',default='snv_testoutput.json')

    args=parser.parse_args()
    loglevel=getattr(logging, args.loglevel.upper(),logging.WARNING)
    if not isinstance(loglevel, int):
            raise ValueError('Invalid log level: %s' % loglevel)
    logging.basicConfig(filename='./structuredMarand2EHRBase.log',filemode='w',level=loglevel)

    inputfile=args.inputfile
    outputfile=args.outputfile
    inputwebtemplate=args.inputwebtemplate
    inputexfile=args.inputexfile
    
    #read composition
    logging.info(f'Reading composition {inputfile}')
    print(f'Reading composition {inputfile}')
    compMARAND=readcomp(inputfile)

    #retrieve template name
    cname=get_composition_name(compMARAND)

    logging.info(f'Template name: {cname}')

    #create flattened version of structured composition
    flattenedcm = flattenpath(compMARAND)
    logging.debug('FLATTENED')
    for fl in flattenedcm:
        logging.debug(fl)

    #read webtemplate
    #in openehrtool gettemp with cname in webtemplate format
    logging.info(f'Reading webtemplate file {inputwebtemplate}')
    print(f'Reading webtemplate file {inputwebtemplate}')
    webtemp=readwt(inputwebtemplate)

    #read example from template in flat format
    #in openehr tool probably the webtemp does not need to be loaded
    logging.info(f'Reading example composition file {inputexfile}')
    print(f'Reading example composition file {inputexfile}')
    extemp=readet(inputexfile)

    compEHRBase={}
    comp={}

    logging.info('Converting ctx')
    print('Converting ctx')
    convert_ctx(compMARAND,comp)

    logging.info('Converting context')
    print('Converting context')
    compcontext=convert_context(compMARAND,cname)
    comp['context']=[]
    comp['context'].append(compcontext)

    logging.info('converting category')
    print('converting category')
    convert_category(compMARAND,comp,cname)

    logging.info('converting content')
    print('converting content')
    convert_content(compMARAND,comp,cname)

    logging.info('Fixing DV_CODED_TEXT leafs')
    print('Fixing DV_CODED_TEXT leafs')
    fixes_dv_coded_text(comp,webtemp,extemp,cname,flattenedcm)

    logging.info('Fixing DV_QUANTITY leafs')
    print('Fixing DV_QUANTITY leafs')
    fixes_dv_quantity(comp,webtemp,extemp,cname,flattenedcm)

    logging.info('Fixing DV_PROPORTION leafs')
    print('Fixing DV_PROPORTION leafs')
    fixes_dv_proportion(comp,webtemp,extemp,cname,flattenedcm)

    logging.info('Fixing DV_COUNT leafs')
    print('Fixing DV_COUNT leafs')
    fixes_dv_count(comp,webtemp,extemp,cname,flattenedcm)

    logging.info('Adding Language and encoding to all entries (i.e. OBSERVATION, ACTION, EVALUATION, ADMIN_ENTRY)')
    print('Adding Language and encoding to all entries (i.e. OBSERVATION, ACTION, EVALUATION, ADMIN_ENTRY)')
    add_language_encoding(comp,webtemp,extemp,cname,flattenedcm)

    #assign temp composition to EHRBase composition
    compEHRBase[cname]=comp
    
    #write EHRBase structured composition to file
    logging.info(f'Writing composition {outputfile}')
    print(f'Writing composition {outputfile}')
    writecomp(outputfile,compEHRBase)


if __name__=="__main__":
    main()
