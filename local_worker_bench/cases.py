"""Independent hand-derived cases. Run only after supervisor source review."""
import ast
import copy
import math


def motor_cases():
    cases = []
    def add(label, args, expected): cases.append((label,args,expected))
    add('disabled_missing',('bad',None,False),'ACTIVE')
    add('disabled_malformed',('ahu',{'supply_fan':'bad'},False),'ACTIVE')
    for kind,key in [('ahu','supply_fan'),('pump','pumps')]:
        for values,want in [([], 'UNKNOWN'),((), 'UNKNOWN'),([None],'UNKNOWN'),
                ([False],'INACTIVE'),([True],'ACTIVE'),([False,None],'UNKNOWN'),
                ([False,True],'ACTIVE'),([None,True],'ACTIVE'),([False,False],'INACTIVE')]:
            add(kind+'_'+repr(values),(kind,{key:values},True),want)
        add(kind+'_missing',(kind,{},True),'UNKNOWN')
        for bad in [None,True,1,'on',{},[True,'bad'],[False,1],[0],[1.0]]:
            add(kind+'_invalid_'+repr(bad),(kind,{key:bad},True),ValueError)
    add('ahu_ignores_return',('ahu',{'supply_fan':[False],'return_fan':[True]},True),'INACTIVE')
    add('ahu_ignores_malformed',('ahu',{'supply_fan':[True],'pumps':'bad'},True),'ACTIVE')
    add('pump_ignores_fan',('pump',{'pumps':[None],'supply_fan':[True]},True),'UNKNOWN')
    add('unsupported_kind',('other',{},True),ValueError)
    add('proofs_wrong_type',('ahu',[],True),ValueError)
    for bad in [0,1,None,'yes']:
        add('required_strict_'+repr(bad),('ahu',{},bad),ValueError)
    return cases


def elapsed_cases():
    h = lambda seconds: seconds/3600.0
    cases = []
    def add(label, rows, gap, expected): cases.append((label,(rows,gap),expected))
    add('empty',[],300,(0.,0.))
    add('single',[(0,True,True)],300,(0.,0.))
    add('healthy_leading',[(0,False,True),(3600,True,True)],7200,(0.,1.))
    add('fault_leading',[(0,True,True),(3600,False,True)],7200,(1.,1.))
    add('unsorted',[(3600,False,True),(0,True,True)],7200,(1.,1.))
    add('last_duplicate_clears',[(0,True,True),(0,False,True),(3600,True,True)],7200,(0.,1.))
    add('last_duplicate_sets',[(0,False,True),(0,True,True),(3600,False,True)],7200,(1.,1.))
    add('nonadjacent_duplicate',[(0,True,True),(3600,True,True),(0,False,True)],7200,(0.,1.))
    add('gap_cap',[(0,True,True),(7200,False,True)],300,(h(300),h(300)))
    add('unknown_fault',[(0,None,True),(300,True,True),(600,False,True)],300,(h(300),h(300)))
    add('unknown_active',[(0,True,None),(300,False,True),(600,False,True)],300,(0.,h(300)))
    add('unknown_next_bounds',[(0,True,True),(300,None,None)],300,(h(300),h(300)))
    add('inactive',[(0,True,False),(300,False,True)],300,(0.,0.))
    add('mixed',[(0,True,True),(300,False,True),(600,True,False),(900,True,True)],300,(h(300),h(600)))
    add('fractional',[(.25,True,True),(.75,False,True)],.3,(h(.3),h(.3)))
    add('negative_epoch',[(-300,True,True),(0,False,True)],300,(h(300),h(300)))
    add('invalid_duplicate_not_erased',[(0,'bad',True),(0,True,True),(300,False,True)],300,ValueError)
    for bad in [0,-1,True,None,float('nan'),float('inf'),'300']:
        add('invalid_gap_'+repr(bad),[],bad,ValueError)
    add('outer_not_list',(),300,ValueError)
    for bad in [True,'0',None,float('nan'),float('inf'),-float('inf')]:
        add('invalid_timestamp_'+repr(bad),[(bad,True,True)],300,ValueError)
    for bad in [1,0,'true',[],{}]:
        add('invalid_fault_'+repr(bad),[(0,bad,True)],300,ValueError)
        add('invalid_active_'+repr(bad),[(0,True,bad)],300,ValueError)
    for row in [None,[],[0,True],(0,True,True,False),{'ts':0}]:
        add('invalid_row_'+repr(row),[row],300,ValueError)
    return cases


def inspect_source(source):
    tree = ast.parse(source)
    banned = {'eval','exec','open','input','compile','getattr','setattr','delattr',
              'globals','locals','vars','__import__','breakpoint','help'}
    for n in ast.walk(tree):
        if isinstance(n,ast.Attribute) and n.attr.startswith('__'):
            benign_type_name = (n.attr=='__name__' and isinstance(n.value,ast.Call)
                and isinstance(n.value.func,ast.Name) and n.value.func.id=='type')
            if not benign_type_name:
                raise ValueError('Dunder attribute in candidate')
        if isinstance(n,ast.Name) and n.id.startswith('__'):
            raise ValueError('Dunder name in candidate')
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in banned:
            raise ValueError('Disallowed call in candidate')
        if isinstance(n,(ast.Import,ast.ImportFrom)):
            names = [a.name for a in n.names] if isinstance(n,ast.Import) else [n.module]
            if any(x != 'math' for x in names):
                raise ValueError('Only math imports allowed')
    for n in tree.body:
        if not isinstance(n,(ast.Import,ast.ImportFrom,ast.FunctionDef)) and not (
                isinstance(n,ast.Expr) and isinstance(n.value,ast.Constant) and isinstance(n.value.value,str)):
            raise ValueError('Top-level executable code in candidate')
    return tree


def execute_reviewed(source, task):
    tree = inspect_source(source)
    def restricted_import(name,*args,**kwargs):
        if name == 'math': return math
        raise ImportError(name)
    builtins = __builtins__ if isinstance(__builtins__,dict) else __builtins__.__dict__
    allowed = ['type','isinstance','ValueError','TypeError','bool','int','float','str',
               'list','tuple','dict','any','all','len','sorted','enumerate','min','max',
               'set','range','zip','iter','sum','round','abs','Exception']
    namespace = {'__builtins__':{k:builtins[k] for k in allowed}|{'__import__':restricted_import},'math':math}
    exec(compile(tree,'<reviewed-local-candidate>','exec'),namespace)
    fn = namespace['motor_gate' if task=='motor' else 'fault_hours']
    return check_function(fn, task)


def check_function(fn, task):
    cases = motor_cases() if task=='motor' else elapsed_cases()
    failures = []
    for label,args,expected in cases:
        before = copy.deepcopy(args)
        actual = None
        try:
            actual = fn(*args)
            if expected is ValueError:
                good = False
            elif task == 'elapsed':
                good = (isinstance(actual,tuple) and len(actual)==2 and all(
                    math.isclose(a,b,rel_tol=1e-9,abs_tol=1e-12) for a,b in zip(actual,expected)))
            else:
                good = actual == expected
        except Exception as e:
            actual = type(e).__name__
            good = expected is ValueError and type(e) is ValueError
        # repr treats paired NaNs consistently and detects modifications to lists/dicts.
        if repr(args) != repr(before):
            good = False
            actual = 'mutated input'
        if not good:
            failures.append({'case':label,'expected':'ValueError' if expected is ValueError else expected,
                             'actual':actual})
    return {'task':task,'passed':len(cases)-len(failures),'total':len(cases),'failures':failures}
