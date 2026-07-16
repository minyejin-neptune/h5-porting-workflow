"""
scan-callers 모드 — 래퍼 호출부 역추적.

이미 플랫폼 처리를 마친 래퍼 클래스의 public 메서드를 가드 없이 호출하는
곳을 찾는다. tree-sitter로 C# AST를 파싱해 변수 타입을 추적하고,
PreprocParser로 해당 호출 줄이 WEBGL-safe 구간인지 확인한다.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from h5_port_verify.core import ConditionClassifier, PreprocParser

_LIFECYCLE_METHODS = {
    'Start', 'Awake', 'Update', 'FixedUpdate', 'LateUpdate',
    'OnDestroy', 'OnEnable', 'OnDisable', 'OnApplicationPause',
    'OnApplicationFocus', 'OnTriggerEnter', 'OnCollisionEnter',
    'OnTriggerExit', 'OnCollisionExit', 'OnDrawGizmos',
}


@dataclass
class CallerHit:
    rel: str
    lineno: int
    caller_var: str    # 호출에 사용된 변수명 또는 클래스명
    wrapper_class: str  # 래퍼 클래스명
    method: str         # 호출된 메서드명


class CallerScanner:
    """
    래퍼 클래스의 public 메서드를 호출하는 파일을 역추적한다.
    tree-sitter로 타입을 추적하고, PreprocParser로 WEBGL 가드를 확인한다.

    지원하는 타입 추론:
      - 명시적 타입 선언: ServiceManager _svc;
      - new 표현식:       var x = new ServiceManager();
      - 제네릭 메서드:    var x = GetComponent<ServiceManager>();
      - 메서드 파라미터:  void Foo(ServiceManager svc)

    추론 불가 케이스 (허용된 한계):
      - var x = GetServiceManager();  (불투명 반환형)
      - 리플렉션·델리게이트 기반 간접 호출
    """

    def __init__(self, classifier: ConditionClassifier):
        self._classifier = classifier
        self._wrappers: dict = {}  # {ClassName: {method1, method2, ...}}
        try:
            from tree_sitter_languages import get_parser as _ts_get
            self._ts_parser = _ts_get('c_sharp')
        except ImportError:
            self._ts_parser = None

    def _get_safe_lines(self, path: Path) -> set:
        """PreprocParser로 WEBGL-safe 줄 번호 집합을 반환한다."""
        safe: set = set()
        parser = PreprocParser(self._classifier)
        for lineno, _code, stack in parser.parse(path):
            if stack.status() == 'SAFE':
                safe.add(lineno)
        return safe

    def _extract_wrapper_info(self, wrapper_file: Path) -> tuple:
        """래퍼 파일에서 (클래스명, public 메서드 집합)을 추출한다."""
        if self._ts_parser is None:
            return ('', set())
        try:
            source = wrapper_file.read_bytes()
        except Exception:
            return ('', set())

        tree = self._ts_parser.parse(source)

        def get_text(node):
            return source[node.start_byte:node.end_byte].decode('utf-8', errors='replace')

        class_name = ''
        methods: set = set()

        def walk(node):
            nonlocal class_name
            if node.type == 'class_declaration':
                for child in node.children:
                    if child.type == 'identifier' and not class_name:
                        class_name = get_text(child)
                for child in node.children:
                    walk(child)
            elif node.type == 'method_declaration':
                is_public = any(
                    get_text(c) == 'public'
                    for c in node.children if c.type == 'modifier'
                )
                if is_public:
                    for child in node.children:
                        if child.type == 'identifier':
                            m = get_text(child)
                            if m not in _LIFECYCLE_METHODS:
                                methods.add(m)
            else:
                for child in node.children:
                    walk(child)

        walk(tree.root_node)
        return (class_name, methods)

    def load_wrappers(self, wrapper_files: list):
        """래퍼 파일들에서 클래스명·메서드 목록을 추출해 내부 dict에 저장한다."""
        for wf in wrapper_files:
            class_name, methods = self._extract_wrapper_info(wf)
            if class_name and methods:
                self._wrappers[class_name] = methods

    def _extract_type_map(self, tree_node, source: bytes) -> dict:
        """AST에서 {변수명: 클래스명} 매핑을 추출한다."""
        type_map: dict = {}
        wrapper_names = set(self._wrappers.keys())

        def get_text(node):
            return source[node.start_byte:node.end_byte].decode('utf-8', errors='replace')

        def infer_from_rhs(rhs) -> str:
            if rhs.type == 'object_creation_expression':
                for c in rhs.children:
                    if c.type == 'identifier' and get_text(c) in wrapper_names:
                        return get_text(c)
            elif rhs.type == 'invocation_expression' and rhs.children:
                fn = rhs.children[0]
                if fn.type == 'generic_name':
                    for c in fn.children:
                        if c.type == 'type_argument_list':
                            for arg in c.children:
                                if arg.type == 'identifier' and get_text(arg) in wrapper_names:
                                    return get_text(arg)
            return ''

        def process_var_decl(vd):
            if not vd.children:
                return
            type_node = vd.children[0]
            if type_node.type == 'identifier':
                tname = get_text(type_node)
                if tname in wrapper_names:
                    for c in vd.children[1:]:
                        if c.type == 'variable_declarator' and c.children:
                            vname = get_text(c.children[0])
                            if vname:
                                type_map[vname] = tname
            elif type_node.type == 'implicit_type':
                for c in vd.children[1:]:
                    if c.type == 'variable_declarator' and c.children:
                        vname = get_text(c.children[0])
                        for sub in c.children:
                            if sub.type == 'equals_value_clause' and sub.children:
                                inferred = infer_from_rhs(sub.children[-1])
                                if inferred and vname:
                                    type_map[vname] = inferred

        def walk(node):
            if node.type in ('field_declaration', 'local_declaration_statement'):
                for c in node.children:
                    if c.type == 'variable_declaration':
                        process_var_decl(c)
            elif node.type == 'parameter':
                ch = node.children
                if len(ch) >= 2 and ch[0].type == 'identifier':
                    tname = get_text(ch[0])
                    if tname in wrapper_names:
                        vname = get_text(ch[-1])
                        if vname:
                            type_map[vname] = tname
            for c in node.children:
                walk(c)

        walk(tree_node)
        return type_map

    def _extract_calls(self, tree_node, source: bytes) -> list:
        """
        AST에서 [(lineno, root_identifier, method_name)] 호출 목록을 추출한다.

        체인 호출 지원: ServiceManager.Instance.ShowVideo()
          → root_identifier = ServiceManager, method_name = ShowVideo
        단일 호출 지원: _svc.ShowVideo()
          → root_identifier = _svc, method_name = ShowVideo
        """
        calls = []

        def get_text(node):
            return source[node.start_byte:node.end_byte].decode('utf-8', errors='replace')

        def root_identifier(node):
            """member_access_expression에서 가장 왼쪽 identifier를 반환한다."""
            cur = node
            while cur.type == 'member_access_expression' and cur.children:
                cur = cur.children[0]
            if cur.type == 'identifier':
                return cur
            return None

        def walk(node):
            if node.type == 'invocation_expression' and node.children:
                mae = node.children[0]
                if mae.type == 'member_access_expression' and len(mae.children) >= 3:
                    mth_n = mae.children[2]
                    root_n = root_identifier(mae.children[0])
                    if root_n is not None and mth_n.type == 'identifier':
                        calls.append((
                            mth_n.start_point[0] + 1,
                            get_text(root_n),
                            get_text(mth_n),
                        ))
            for c in node.children:
                walk(c)

        walk(tree_node)
        return calls

    def scan_file(self, path: Path, base: Path, wrapper_rels: set) -> list:
        if self._ts_parser is None:
            return []
        try:
            rel = str(path.relative_to(base))
        except ValueError:
            rel = str(path)
        if rel in wrapper_rels:
            return []
        try:
            source = path.read_bytes()
        except Exception:
            return []

        safe_lines = self._get_safe_lines(path)
        tree = self._ts_parser.parse(source)
        type_map = self._extract_type_map(tree.root_node, source)
        calls = self._extract_calls(tree.root_node, source)

        results = []
        for lineno, obj_name, method_name in calls:
            if lineno in safe_lines:
                continue
            if obj_name in self._wrappers:
                resolved = obj_name
            elif obj_name in type_map:
                resolved = type_map[obj_name]
            else:
                continue
            if method_name not in self._wrappers.get(resolved, set()):
                continue
            results.append(CallerHit(rel, lineno, obj_name, resolved, method_name))

        return results

    def scan(self, scan_files: list, base: Path, wrapper_rels: set) -> list:
        results = []
        with ThreadPoolExecutor() as exe:
            futs = [exe.submit(self.scan_file, f, base, wrapper_rels) for f in scan_files]
            for fut in as_completed(futs):
                results.extend(fut.result())
        results.sort(key=lambda h: (h.rel, h.lineno))
        return results
