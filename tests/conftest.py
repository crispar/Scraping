"""테스트 공통 설정: 패키지 설치(pip install -e .) 없이도 src/ 와 루트 모듈을 import 할 수 있게 한다."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for path in (os.path.join(ROOT, 'src'), ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)
