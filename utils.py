import js, re, json
from pyscript import web, document
from pyscript.ffi import to_js, create_proxy
from pyscript.util import is_awaitable
from pyscript.fetch import fetch

#exports Debug, showerrpor, after, when, J, setTimeout, setInterval, ServerComm


class ToJs:
    def __getitem__(self, index): return self.__call__(index)
    def __call__(self, arg): 
        if callable(arg):
            return create_proxy(arg)
        return to_js(arg)
    def __lshift__(self, other): return self.__call__(other)
    def __rrshift__(self, other): return self.__call__(other)
    def __or__(self, other): return self.__call__(other)
    def __ror__(self, other): return self.__call__(other)
    
J = ToJs()  

def setTimeout(fn, ms):
    js.setTimeout(J<<fn, ms)

def setInterval(fn, ms):
    js.setInterval(J<<fn, ms)


class Debug:
    def __init__(self, debug):
        #print("Init")
        self.debug = debug
    def __call__(self, msg, *, nodebug=False):
        #print("No Call")
        if web.page['test'] is None:
            web.page.body.append(web.div(id='test', class_='debug'))
        if not nodebug and not self.debug: 
            return
        web.page["test"].innerHTML = f'{msg}<br>{ web.page["test"].innerHTML }'
        return None


debug = Debug(False)

# decorator show error
def showerror(fct):
    if is_awaitable(fct):
        async def decorate(*args, **kwargs):
            try:
                return await fct(*args, **kwargs)
            except Exception as e:
                debug(f"<br>ERROR in {fct.__name__}: { e }", nodebug=True)
    else:
        def decorate(*args, **kwargs):
            try:
                return fct(*args, **kwargs)
            except Exception as e:
                debug(f"<br>ERROR in {fct.__name__}: { e }", nodebug=True)
    return decorate

#decorator after
def after(ms=100):
    def decorator(callback):
        def decorate(*args, **kwargs):
            setTimeout(lambda: callback(*args, **kwargs), ms)
        return decorate
    return decorator
    


    
#decorator when
def when(event, selector):
    class decorator:
        def __init__(self, fn):
            self.fn = fn
            self.func = lambda *args, **kwargs: self.fn(*args, **kwargs)
            for elem in web.page.find(selector): 
                elem.addEventListener(event, self.func)
        def __call__(self, *args, **kwargs): 
            return self.fn(*args, **kwargs)
        def __set_name__(self, owner, name):
            for elem in web.page.find(selector):
                elem.removeEventListener(event, self.func)
                elem.addEventListener(event, J(lambda *args, **kwargs: self.fn(owner.instance, *args, **kwargs)))
            setattr(owner, name, self.func)
    return decorator


    
class ServerComm:
    
    @showerror
    def __init__(self, refresh=0, timer=0):
        self.refreshTimer = lambda ms=refresh: setTimeout(self.refresh, ms) if ms else ''
        if timer:
            evt = js.CustomEvent.new('timer')
            setInterval(lambda: self.dispatchTimerEvent(evt), timer)
        self.sessionID = self.getCookie('sessionID')
        if self.sessionID is not None:
            self.refreshTimer()
        if 'exported' in globals():
            for fname in exported:
                setattr(self, fname, lambda *args: self.execMethod(fname, *args))
        #debug('ServerComm')
             
    
    
    @showerror
    def getCookie(self, name, default=None):
        cookie = document.cookie
        if len(cookie):
            regm = re.search(f"{name.lower()}=([^;]*|$)", cookie)
            if regm is not None:
                return regm.group(1)
        return default
        
     
    @showerror
    async def refresh(self):
        #debug(f"checkRefresh {self.sessionID}")
        ok, data = await self.send('refresh', { 'sessionid': self.sessionID, 'message': 'refresh', })
        if ok:
            self.refreshTimer()
        else:
            debug(f"Nok")
            js.location.reload() 
    
    @showerror
    def dispatchTimerEvent(self, event):
        web.page.body.dispatchEvent(event)
        #debug("dispatch")
        
        
    #@showerror
    async def execMethod(self, method, *args):
        ok, data = await self.send('command', { 'sessionid': self.sessionID, 'message': 'command', 
                                            'command': method, 'arguments': args })
        if ok and 'result' in data:
            return data['result']
        else:
            raise Exception(f"{data['result']}")
        return None
                
    #@showerror
    async def send(self, path, body):
        response = await fetch(f'{js.location.href}/{path}', 
            method='POST', 
            headers={"Content-Type": "application/json"}, 
            body=json.dumps(body), 
            )
        data = None
        #if response.ok:
        data = await response.json()
        return (response.ok, data)
   
