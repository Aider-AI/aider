

from openai import OpenAI

from aider import env
from aider.coders.base_coder import Coder
from aider.models import Model
OPENAI_API_KEY = ''
BASE_URL = 'https://api.openai.com/v1'
BASE_MODEL = 'azure/fume-gpt-4o-global'
task = '''Refactor Login.js to use local state
Remove the import of useLoginContext and useRegisterContext. - Replace the usage of loginData, setLoginData, loginPending, setLoginPending, loggedIn, setLoggedIn, loginFailMessage, and setLoginFailMessage with local state variables. - Update the handleChange and handleSubmit functions to use the local state variables.'''
files=['/Users/metehanoz/FumeData/metehanozdev-ecohabit-main/client/src/components/Login.js']
task_id = 'metehanozdev-ecohabit-main'


client = OpenAI(api_key=OPENAI_API_KEY,base_url=BASE_URL)
model = Model(model=BASE_MODEL)
model.edit_format = 'diff-fenced'

coder = Coder.create(fnames=files, main_model=model,use_git= False,task_id=task_id,api_key=OPENAI_API_KEY,base_url=BASE_URL,edit_format='diff-fenced')
coder.run(task)