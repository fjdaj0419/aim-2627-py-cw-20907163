---
alwaysApply: false
description: 
---
CI 检查四项
①只允许修改 src/main/** 与 README.md（tools、src/tests/、.github/ 改了直接红）；②
autopep8 风格（--diff 非空即败）；③可见 pytest；④ commit 粒度软检查（≥ 15 个、信息有意
义——只做提示不拦车）。