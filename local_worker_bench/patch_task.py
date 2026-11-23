"""Compact synthetic HTTP-status patch task and independently derived cases."""
PROMPT='''Patch this broken Python function: def is_success(status): return bool(status)
Return JSON only with a source string containing the complete replacement function.
Contract: return an actual bool. True only when type(status) is exactly int and its value is 200 through 299 inclusive. Return False for every other value, including bool, float, str, None, containers and int subclasses. No imports, I/O or side effects. Keep the source compact; no explanation or test claims.'''


def cases():
    class StatusInt(int):pass
    return [('below',199,False),('lower',200,True),('created',201,True),('empty',204,True),
        ('middle',250,True),('upper',299,True),('redirect',300,False),('moved',301,False),
        ('bad',400,False),('auth',401,False),('missing',404,False),('rate_limit',429,False),
        ('error',500,False),('last_error',599,False),('outside',600,False),('zero',0,False),
        ('negative',-1,False),('none',None,False),('true',True,False),('false',False,False),
        ('float',200.0,False),('string','200',False),('list',[],False),('dict',{},False),
        ('int_subclass',StatusInt(200),False)]


def grade(fn):
    failures=[]
    for label,value,expected in cases():
        before=repr(value)
        try:
            actual=fn(value);good=type(actual) is bool and actual==expected and repr(value)==before
        except Exception as error:actual=type(error).__name__;good=False
        if not good:failures.append(dict(case=label,expected=expected,actual=actual))
    return dict(task='patch',passed=25-len(failures),total=25,failures=failures)
