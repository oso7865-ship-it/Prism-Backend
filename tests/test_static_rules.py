import asyncio

import pytest

from app.domain.analysis.analyzer import evaluate
from app.domain.analysis.contracts import MAX_FILE, RULES
from app.domain.analysis.parser_process import parse_file
from app.domain.analysis.pipeline import changed_lines, safe_path
from app.shared.github.client import GitHubFailure

# Every active rule has two violations, two normal inputs and a lookalike normal input.
CASES = {
    "COM-003": (
        "a.js",
        [
            "if(a){if(b){if(c){if(d){if(e){work();}}}}}",
            "while(a){for(;;){if(b){while(c){if(d){break;}}}}}",
        ],
        [
            "if(a){if(b){if(c){if(d){work();}}}}",
            "if(a){}else if(b){}else if(c){}else if(d){}else if(e){}",
            "const s='if(a){if(b){if(c){if(d){if(e){}}}}}';",
        ],
    ),
    "PY-004": (
        "a.py",
        ["eval(value)", "def f(x):\n return eval(x)"],
        ["parse(value)", "obj.eval(value)", "def f(eval):\n return eval(value)"],
    ),
    "PY-005": (
        "a.py",
        ["exec(value)", "def f(x):\n exec(x)"],
        ["execute(value)", "obj.exec(value)", "exec = custom\nexec(value)"],
    ),
    "PY-008": (
        "a.py",
        [
            "try:\n work()\nexcept Exception:\n raise",
            "try:\n work()\nexcept BaseException as e:\n log(e)",
        ],
        [
            "try:\n work()\nexcept ValueError:\n raise",
            "try:\n work()\nexcept Exception:\n pass",
            "Exception = CustomError\ntry:\n work()\nexcept Exception:\n raise",
        ],
    ),
    "JS-005": (
        "a.js",
        ["eval(value);", "function f(x){return eval(x);}"],
        ["parse(value);", "obj.eval(value);", "function f(eval){return eval(value);}"],
    ),
    "JS-006": (
        "a.ts",
        ["new Function(value);", "Function('x', value);"],
        [
            "new Other(value);",
            "const s='new Function(value)';",
            "class Function {} new Function(value);",
        ],
    ),
    "JAVA-004": (
        "a.java",
        [
            "class A { void f(){try{}catch(Exception e){}}}",
            "class B {void g(){try{}catch(Throwable e){/*intentional*/}}}",
        ],
        [
            "class A {void f(){try{}catch(Exception e){throw e;}}}",
            "class A {}",
            'class A {String s="catch(Exception e){}";}',
        ],
    ),
    "JAVA-005": (
        "a.java",
        ["import java.util.*; class A {}", "import static java.util.Collections.*; class A {}"],
        ["import java.util.List; class A {}", "class B {}", "// import java.util.*;\nclass A {}"],
    ),
    "JAVA-006": (
        "a.java",
        ["class A {void f(){while(true);}}", "class A {void f(){for(;;);}}"],
        [
            "class A {void f(){while(true){break;}}}",
            "class B {}",
            "class A {void f(){for(;;){break;}}}",
        ],
    ),
    "JAVA-007": (
        "a.java",
        ["class A {public static int x;}", "class A {static public String y;}"],
        [
            "class A {public static final int x=1;}",
            "class A {private static int x;}",
            "class A {public static void f(){}}",
        ],
    ),
    "JAVA-008": (
        "a.java",
        [
            'class A {boolean f(String s){return s=="x";}}',
            'class A {boolean f(String s){return "y"!=s;}}',
        ],
        [
            "class A {boolean f(int i){return i==1;}}",
            'class A {boolean f(String s){return s.equals("x");}}',
            'class A {String s="a==b";}',
        ],
    ),
    "PY-001": (
        "a.py",
        ["def f(a=[]): pass", "def f(a: dict={}): pass"],
        ["def f(a=None): pass", "def f(a=()): pass", 's="def f(a=[]): pass"'],
    ),
    "PY-002": (
        "a.py",
        ["try:\n x()\nexcept:\n pass", "try:\n x()\nexcept:\n raise"],
        ["try:\n x()\nexcept ValueError:\n raise", "def f(): pass", 's="except:"'],
    ),
    "PY-003": (
        "a.py",
        [
            "try:\n x()\nexcept ValueError:\n pass",
            "try:\n x()\nexcept Exception:\n # intentional\n pass",
        ],
        ["try:\n x()\nexcept Exception:\n raise", "def f(): pass", "try:\n x()\nexcept:\n pass"],
    ),
    "PY-006": (
        "a.py",
        ["from x import *", "from a.b import *"],
        ["from x import y", "import x", 's="from x import *"'],
    ),
    "JS-001": (
        "a.js",
        ["var x=1;", "function f(){var y=2;}"],
        ["let x=1;", "const y=2;", 'const s="var x=1";'],
    ),
    "JS-002": ("a.js", ["a == b;", "a != 1;"], ["a === b;", "a == null;", 'const s="a == b";']),
    "JS-003": (
        "a.js",
        ["debugger;", "function f(){debugger;}"],
        ["const x=1;", "function f(){}", 'const s="debugger;";'],
    ),
    "JS-004": (
        "a.js",
        ["try{}catch(e){}", "try{}catch{/*ignore*/}"],
        ["try{}catch(e){throw e;}", "function f(){}", 'const s="catch(e){}";'],
    ),
    "TS-001": (
        "a.ts",
        ["let a:any;", "function f(a:any){}"],
        ["let a:unknown;", "let a:string;", 'const s="any";'],
    ),
    "TS-002": (
        "a.ts",
        ["// @ts-ignore\nlet a=1;", "/* @ts-ignore */\nlet a=1;"],
        ["// @ts-expect-error\nlet a=1;", "let a=1;", 'const s="// @ts-ignore";'],
    ),
    "TS-003": (
        "a.ts",
        ["// @ts-nocheck\nlet a=1;", "/* @ts-nocheck */\nlet a=1;"],
        ["// @ts-check\nlet a=1;", "let a=1;", 'const s="// @ts-nocheck";'],
    ),
    "TS-004": (
        "a.ts",
        ["x!.foo();", "let y=x!;"],
        ["!x;", "class A {x!:string;}", 'const s="x!";'],
    ),
    "TS-005": (
        "a.ts",
        ["const x=y as unknown as string;", "const x=y as any as number;"],
        ["const x=y as string;", "const x=y as unknown;", 'const s="as unknown as";'],
    ),
    "COM-001": ("a.py", ["# a\n" * 501, "# b\r\n" * 502], ["# a\n" * 500, "x=1", 's="500"']),
    "COM-002": (
        "a.py",
        [
            "def f():\n" + (" # comment\n" * 60) + " pass",
            "async def f():\r\n" + (" # comment\r\n" * 60) + " pass",
        ],
        ["def f(): pass", "def f():\n" + (" # comment\n" * 57) + " pass", 's="def f():"'],
    ),
    "COM-004": (
        "a.py",
        ["def f(a,b,c,d,e,f): pass", "def f(self,a,b,c,d,e,*args): pass"],
        ["def f(a,b,c,d,e): pass", "def f(self,a,b,c,d,e): pass", 's="def f(a,b,c,d,e,f):"'],
    ),
    "COM-009": (
        "a.txt",
        ["ghp_" + "a" * 36, "AKIA" + "B" * 16],
        ["ghp_placeholder", "AKIA_EXAMPLE", "ghp_" + "a" * 37],
    ),
    "COM-010": (
        "a.txt",
        [
            "-----BEGIN " + "PRIVATE KEY-----\nexample\n-----END PRIVATE KEY-----",
            "-----BEGIN " + "RSA PRIVATE KEY-----\nexample\n-----END RSA PRIVATE KEY-----",
        ],
        [
            "PRIVATE KEY placeholder",
            "-----BEGIN PUBLIC KEY-----\nx\n-----END PUBLIC KEY-----",
            "// private key documentation",
        ],
    ),
}


@pytest.mark.parametrize("rule", sorted(CASES))
def test_rule_activation_fixtures(rule):
    path, bad, good = CASES[rule]
    for source in bad:
        result = evaluate(path, source.encode())
        matches = [f for f in result.findings if f.rule_id == rule]
        assert matches, (rule, result)
        assert all(f.start_line >= 1 and f.end_line >= f.start_line for f in matches)
        assert result.status == "INCLUDED"
    for source in good:
        result = evaluate(path, source.encode())
        assert rule not in {f.rule_id for f in result.findings}, (rule, source)
        assert result.status == "INCLUDED"
    assert RULES[rule].severity in ("INFO", "WARNING", "ERROR", "CRITICAL")


def test_every_active_rule_has_activation_fixtures():
    assert set(CASES) == set(RULES)


@pytest.mark.parametrize(
    "path,source",
    [
        ("x.java", "class A {void f(int a,int b,int c,int d,int e,int f){}}"),
        ("x.js", "function f(a,b,c,d,e,f){}"),
        ("x.jsx", "const x=<div/>; function f(a,b,c,d,e,f){}"),
        ("x.mjs", "function f(a,b,c,d,e,f){}"),
        ("x.cjs", "function f(a,b,c,d,e,f){}"),
        ("x.ts", "function f(a:number,b:number,c:number,d:number,e:number,f:number){}"),
        ("x.tsx", "const x=<div/>; function f(a,b,c,d,e,f){}"),
        ("x.mts", "function f(a,b,c,d,e,f){}"),
        ("x.cts", "function f(a,b,c,d,e,f){}"),
        ("x.py", '@decorator\ndef f(a,b,c,d,e,f):\n\treturn "한글"'),
    ],
)
def test_language_extensions_and_parameters(path, source):
    result = evaluate(path, source.encode())
    assert result.status == "INCLUDED"
    assert "COM-004" in {f.rule_id for f in result.findings}


@pytest.mark.parametrize("path", ["x.java", "x.js", "x.ts", "x.py"])
def test_parse_failure_size_and_capability(path):
    result = evaluate(path, b"\x01\xff")
    assert result.reason == "ENCODING_UNSUPPORTED"
    assert evaluate(path, b"x" * (MAX_FILE + 1)).status == "LIMIT_EXCEEDED"
    result = evaluate(path, b"function { def (( class ")
    assert result.status == "PARSE_ERROR" and result.not_evaluated


def test_secret_free_result_caps_and_excluded_source():
    secret = "ghp_" + "Z" * 36
    result = evaluate("x.py", ("# " + secret + "\n").encode() * 105)
    assert len(result.findings) == 100 and result.limit
    assert secret not in result.model_dump_json()
    assert evaluate("x.vue", b"<script>debugger;</script>").reason == "SECRET_SCAN_ONLY"
    assert evaluate("x.d.ts", b"declare let a:any;").reason == "SECRET_SCAN_ONLY"
    assert evaluate("x.js", b"debugger;", True).reason == "IGNORED_SOURCE_RULES"


def test_process_timeout_and_output():
    result = asyncio.run(parse_file("x.js", b"debugger;"))
    assert result.findings[0].rule_id == "JS-003"
    result = asyncio.run(parse_file("x.js", b"debugger;", timeout=0.00001))
    assert result.reason == "PARSER_TIMEOUT"


def test_process_cancellation_reaps_child(monkeypatch):
    import subprocess

    original = subprocess.Popen
    children = []

    def tracked(*args, **kwargs):
        child = original(*args, **kwargs)
        children.append(child)
        return child

    monkeypatch.setattr("app.domain.analysis.parser_process.subprocess.Popen", tracked)

    async def cancel():
        task = asyncio.create_task(parse_file("x.js", b"debugger;"))
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(cancel())
    assert len(children) == 1 and children[0].poll() is not None


def test_patch_completeness_and_path():
    assert changed_lines("@@ -1,1 +1,2 @@\n-old\n+new\n+more", 2, 1) == {1, 2}
    assert changed_lines("@@ -1,1 +1,2 @@\n-old\n+new", 2, 1) is None
    assert changed_lines(None, 2, 1) is None
    for path in ["../a", "a/../../b", "/etc/passwd", "a\\b", "a\nsecret"]:
        with pytest.raises(GitHubFailure):
            safe_path(path)
    assert safe_path("src/한글 A.java") == "src/한글 A.java"
