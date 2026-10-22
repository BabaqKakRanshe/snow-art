#!/bin/bash
# before / after composites for every view; args: extra json for v11 (optional)
cd /home/claude/plane/v11/prev
X=${1:-'{}'}
python3 urp_emulate.py r/ext_front v10 r/v10_ext_front.png '{"beacon_top":-60}' | tail -1
python3 urp_emulate.py r/ext_front v11 r/v11_ext_front.png "$(python3 -c "import json;d={'beacon_top':-60,'beacon_bottom':-100};d.update(json.loads('$X'));print(json.dumps(d))")" | tail -1
python3 urp_emulate.py r/ext_front v11 r/v11_ext_front_strobe.png "$(python3 -c "import json;d={'beacon_top':-60,'beacon_bottom':-100,'levels':{'strobe':1}};d.update(json.loads('$X'));print(json.dumps(d))")" | tail -1
python3 urp_emulate.py r/ext_rear v10 r/v10_ext_rear.png '{}' | tail -1
python3 urp_emulate.py r/ext_rear v11 r/v11_ext_rear.png "$(python3 -c "import json;d={'beacon_top':140,'beacon_bottom':60};d.update(json.loads('$X'));print(json.dumps(d))")" | tail -1
python3 urp_emulate.py r/ext_far v10 r/v10_ext_far.png '{}' | tail -1
python3 urp_emulate.py r/ext_far v11 r/v11_ext_far.png "$(python3 -c "import json;d={'beacon_top':30,'beacon_bottom':-150};d.update(json.loads('$X'));print(json.dumps(d))")" | tail -1
python3 urp_emulate.py r/int_cockpit v10 r/v10_int_cockpit.png '{}' | tail -1
python3 urp_emulate.py r/int_cockpit v11 r/v11_int_cockpit.png "$X" | tail -1
python3 urp_emulate.py r/int_bay v10 r/v10_int_bay.png '{}' | tail -1
python3 urp_emulate.py r/int_bay v11 r/v11_int_bay.png "$X" | tail -1
