$ErrorActionPreference = 'Continue'
$conda = 'D:\Tool\anaconda3\Scripts\conda.exe'
$envp  = 'D:\Tool\anaconda3\envs\bizflow'
$py    = Join-Path $envp 'python.exe'
$proj  = 'D:\pyhton\python项目\fastapixxxmmm'
$log   = 'D:\pyhton\python项目\fastapixxxmmm\env_setup.log'
$mirror = 'https://pypi.tuna.tsinghua.edu.cn/simple'

function Log($m) { Add-Content -Path $log -Value ("[{0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $m) }
Set-Content -Path $log -Value ("start at " + (Get-Date))

if (-not (Test-Path $py)) {
    Log 'creating conda env bizflow (python 3.12)...'
    & $conda create -n bizflow python=3.12 -y *>> $log
} else { Log 'env already exists, skip create' }

Log ('python: ' + (& $py --version 2>&1))

Log 'upgrading pip...'
& $py -m pip install --upgrade pip -i $mirror *>> $log

Log 'installing requirements.txt (this takes a while)...'
& $py -m pip install -r (Join-Path $proj 'requirements.txt') -i $mirror --timeout 180 --retries 5 *>> $log
Log ('pip exit code = ' + $LASTEXITCODE)

Log 'verify imports...'
& $py -c "import fastapi, langchain, langchain_ollama, chromadb, sqlalchemy, alembic, uvicorn, redis, torch, sentence_transformers, jieba, tiktoken, pydantic; print('CORE_OK')" *>> $log
& $py -c "import torch; print('torch', torch.__version__, 'cuda', torch.cuda.is_available())" *>> $log
& $py -c "import chromadb; print('chromadb', chromadb.__version__)" *>> $log
& $py -c "import langchain; print('langchain', langchain.__version__)" *>> $log
Log 'done'
