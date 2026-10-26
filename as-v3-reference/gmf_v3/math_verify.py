"""Bounded symbolic checks. Never eval/sympify untrusted strings; never certify physics."""
import ast
import multiprocessing as mp
from .contracts import MathCheck


def _expression(text):
    import sympy as s
    tree=ast.parse(text.replace("^","**"),mode="eval")
    if len(list(ast.walk(tree)))>100: raise ValueError("expression too complex")
    def visit(n):
        if isinstance(n,ast.Expression): return visit(n.body)
        if isinstance(n,ast.Constant) and type(n.value) in {int,float} and abs(n.value)<=1e6:
            return s.Rational(str(n.value))
        if isinstance(n,ast.Name) and n.id.isalnum() and len(n.id)<=16:
            return {"pi":s.pi,"E":s.E}.get(n.id,s.Symbol(n.id,real=True))
        if isinstance(n,ast.UnaryOp) and isinstance(n.op,(ast.UAdd,ast.USub)):
            value=visit(n.operand);return value if isinstance(n.op,ast.UAdd) else -value
        if isinstance(n,ast.BinOp):
            a,b=visit(n.left),visit(n.right)
            if isinstance(n.op,ast.Add): return a+b
            if isinstance(n.op,ast.Sub): return a-b
            if isinstance(n.op,ast.Mult): return a*b
            if isinstance(n.op,ast.Div): return a/b
            if isinstance(n.op,ast.Pow) and b.is_number and abs(b)<=12: return a**b
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and not n.keywords and len(n.args)==1:
            funcs={"sin":s.sin,"cos":s.cos,"tan":s.tan,"sqrt":s.sqrt,"exp":s.exp,"log":s.log,"abs":s.Abs}
            if n.func.id in funcs: return funcs[n.func.id](visit(n.args[0]))
        raise ValueError("unsupported expression syntax")
    return visit(tree)


def _worker(payload,queue):
    try:
        import sympy as s
        check=MathCheck.model_validate(payload)
        a,b=_expression(check.lhs),_expression(check.rhs)
        x=s.Symbol(check.variable,real=True)
        if check.kind=="derivative": a=s.diff(a,x)
        elif check.kind=="integral": a=s.integrate(a,x)
        elif check.kind=="solve":
            solutions=s.solve(a,x)
            queue.put({"passed":any(s.simplify(sol-b)==0 for sol in solutions),"result":[str(v) for v in solutions],"scope":"symbolic_only"})
            return
        result=s.simplify(a-b)
        queue.put({"passed":bool(result==0),"result":str(result),"scope":"symbolic_only"})
    except Exception as exc:
        queue.put({"passed":None,"error":type(exc).__name__,"scope":"symbolic_only"})


def verify(check: MathCheck,timeout=4):
    ctx=mp.get_context("spawn")
    queue=ctx.Queue()
    p=ctx.Process(target=_worker,args=(check.model_dump(),queue))
    p.start();p.join(timeout)
    if p.is_alive():
        p.terminate();p.join();queue.close()
        return {"passed":None,"error":"timeout","scope":"symbolic_only"}
    try: return queue.get(timeout=1)
    except Exception: return {"passed":None,"error":"worker_failed","scope":"symbolic_only"}
    finally: queue.close()

