# StructuredMarandDesigner2EHRBase
Convert from Marand Archetype Designer structured format to EHRBase format

Flags in brief:
loglevel=set level for the log file conversion.log
inputfile=structured composition input file returned from Archetype Designer Form
inputwebtemplate=template in EHRBase webtemplate format
outputfile=output filename
inputexfile=example composition in flat format from EHRBase

Use example:
python3 structuredMarand2EHRBase.py --loglevel=INFO --inputfile=pippoAD.json --inputexfile=pippoexamplecompflat.json --webtemplate=pippowebtemplateEHRBase.json --outputfilebasename=pippoEHRBase.json 
