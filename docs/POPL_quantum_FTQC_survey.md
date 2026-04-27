# POPL 量子程序语言论文与容错量子计算选题调研

日期：2026-04-27

范围：Zotero collection `reference/POPL` 当前包含 21 篇 POPL 量子相关论文。本文重新整理这些论文的研究主题、问题意识、技术路线和写作范式，并结合近期容错量子计算（FTQC）方向，分析哪些主题更适合投稿 POPL 2027。

说明：collection 中 `On Circuit Description Languages, Indexed Monads, and Resource Analysis` 在 Zotero 中标为 preprint，但已被你放入 POPL collection，本文按 POPL 相关论文一并分析。

## 总体判断

近几年 POPL 量子论文有一个非常清楚的共性：它们并不是简单把量子计算中的一个物理协议搬到 PL 社区，而是把量子计算中的某个难以组合、难以验证、难以编译或难以表达的对象，重塑成一个可编程、可推理、可静态分析的抽象。

成功论文通常满足四点：

- 有明确的软件痛点：低层 circuit 难写、资源不可控、证明不可自动化、参数化电路不可验证、硬件后端差异太大、量子测量和 classical control 难以形式化。
- 有小而硬的形式核心：语言、类型系统、逻辑、自动机、语义模型、IR 或 DSL。
- 有明确的正确性叙事：soundness、completeness、full abstraction、relative completeness、decidability、type safety、optimizer correctness、resource bound soundness。
- 有非玩具级证据：实现、case studies、benchmark、机械化证明、真实后端、主流算法表达或与已有工具比较。

因此，如果目标是 POPL 2027，主题应避免只做“新的 magic state distillation 协议”或“新的 code switching 物理方案”。这些可以作为动机和后端实例，但 POPL 主贡献最好是：

**面向 universal fault-tolerant quantum computation 的代码索引类型系统、资源效果系统、逻辑或编译器 IR。**

最值得推进的主线是：

**Code-indexed, resource-aware fault-tolerant quantum programming.**

核心想法是把 logical qubit 当前所在的 QECC code、code switching、transversal gate 能力、magic-state/cultivation/factory 资源、postselection/failure、decoder/feedforward latency、logical error budget 等全部变成程序层面的类型、能力和效果，从而支持组合式验证和优化编译。

## 逐篇论文调研

### 1. Generating Compilers for Qubit Mapping and Routing

链接：https://doi.org/10.1145/3776720

**解决的问题。** 量子电路要在具体量子处理器上运行，必须把 circuit qubits 映射到 processor qubits，并安排指令执行，使其满足硬件连接、移动、并行度、错误校正等约束。这就是 qubit mapping and routing（QMR）问题。以往大量工作针对特定硬件或特定约束手写 QMR 编译器，导致方法碎片化、复用性差，面对快速演化的量子硬件很难维护。

**面临的挑战。** QMR 的困难不只是图上插入 SWAP。不同处理器的状态变化、可执行操作、约束和代价模型差异很大：超导、离子阱、可移动中性原子、error-corrected logical qubits 都可能有不同的 device dynamics。若抽象过弱，无法覆盖真实硬件；抽象过强，又难以生成高质量编译器。论文的挑战是找到一个足够统一但仍能表达具体后端差异的核心模型。

**核心思想和技术。** 论文抽象出 `device state machine` 作为 QMR 问题的共同核心。用户用一个紧凑 DSL 描述硬件状态、可用动作、约束和代价；系统再用一个参数化 QMR 算法生成对应编译器。换句话说，论文把“为每种设备写一个编译器”的任务，转化为“声明设备状态机 + 自动实例化通用算法”。

**优势与效果。** 这种方法降低了新硬件后端的编译器开发成本，并且生成的编译器在多个重要 QMR case study 中，运行时间和 solution quality 能与手写专用编译器竞争。其价值在于把硬件多样性压缩到一个声明式接口里，而不是不断积累特殊 pass。

**写作整体逻辑。** 文章采用典型系统型 POPL 结构：先指出领域碎片化，再提出统一抽象；接着定义 DSL 和抽象 QMR 问题；然后给出通用算法；最后用多后端 case studies 证明“生成式方法并不牺牲质量”。它不是从理论漂亮性出发，而是从工程生态不可持续出发，再给出形式化核心。

**语言风格。** 语言务实、系统化，强调“diverse and fast-evolving hardware landscape”带来的维护压力。叙事上少用深奥数学，多用抽象接口、问题归约和实验对比。它给 FTQC 选题的启发是：如果 code switching、magic-state factory、logical routing 的后端差异很大，可以考虑做生成式/声明式编译框架，而不是一个固定后端优化器。

### 2. On Circuit Description Languages, Indexed Monads, and Resource Analysis

链接：Zotero 条目为 preprint；主题对应 Proto-Quipper / circuit description language / resource analysis。

**解决的问题。** Quipper/Proto-Quipper 这类 circuit description language 的本质是：程序求值产生一个普通值，同时作为副作用生成一个量子电路。传统语义若把值和电路混在一起，很难解释“程序生成了多大的电路”这类资源性质，也难以为资源受控的类型系统提供语义基础。

**面临的挑战。** Circuit generation 是一种复杂副作用，但它不是普通 state monad 那样的状态变化。程序的返回值与生成电路之间存在依赖；优化会改变生成电路的形态但不应破坏语义；资源类型系统需要证明的是“生成电路满足定量边界”，而不仅是程序本身类型正确。因此需要一种能同时分离值、保留电路副作用、支持优化与资源分析的语义模型。

**核心思想和技术。** 论文引入基于 indexed monads 的 denotational model，把 term reduce 到的值与 term 产生的 circuit side effect 分离。关键新概念是 `circuit algebra`：它抽象电路组合、优化和度量，使 effect typing 可以保证生成电路的 quantitative properties。Indexed monad 的作用是记录不同阶段、不同 circuit effect 的索引变化。

**优势与效果。** 该框架为 Proto-Quipper 家族提供 adequacy，并为资源类型系统的语义正确性提供统一基础。它的价值不在于提出某个新资源估计器，而在于给后续 width/depth/gate count/resource effect analysis 一个可复用的语义底座。

**写作整体逻辑。** 文章逻辑偏理论：先说明 circuit description language 的语义难点，再引入 monadic separation；随后定义 circuit algebra 和 indexed monadic model；再说明如何解释 Proto-Quipper 与资源类型系统；最后把它和优化场景连接起来。它的叙事关键词是“separate value from generated circuit”。

**语言风格。** 写法抽象、范畴/语义味较强，但动机非常 PL：生成代码的副作用如何建模，资源性质如何由类型保证。对 FTQC 的启发是：fault-tolerant compilation 也天然有“返回逻辑计算 + 生成 syndrome schedule/code switch/factory plan”的双重输出，indexed monads 或 effect algebras 很适合表达这种结构。

### 3. Automating Equational Proofs in Dirac Notation

链接：https://doi.org/10.1145/3704878

**解决的问题。** Dirac notation 是量子物理和量子程序语言中表达 quantum states、operators、inner products 的标准记法，但人工等式证明繁琐且容易出错。已有量子程序验证工具若不能自动处理 Dirac 等式，就会把大量证明负担留给用户。

**面临的挑战。** Dirac notation 看似是线性代数记法，实际包含复数、张量、求和、内积、外积、正规化、符号变量等多层结构。一般的一阶理论可能不可判定或效率很差。论文需要说明：哪些 Dirac 公式可以自动判定？如何避免把所有问题都交给昂贵的实闭域判定？如何在大量文献例子上实用？

**核心思想和技术。** 论文先给出理论上限：Dirac notation 的一阶理论可归约到 real closed fields，因此由 Tarski 定理得到 decidability。然后给出实用算法：用 term rewriting 高效判定等式有效性。它把 Dirac 表达式规范化，利用重写规则消除记法层面的差异，从而做 equivalence checking。

**优势与效果。** 理论上有 decidability，实践上有 Mathematica 实现，并在 100 多个文献例子上展示效率。这种“双层贡献”很适合 POPL：先证明问题可判定，再给出可用算法，而不是停留在存在性证明。

**写作整体逻辑。** 文章先从用户熟悉但工具不擅长的 notation 入手，说明自动化缺口；然后给出 general decidability result；再把重心转向高效 rewriting algorithm；最后用例子库证明覆盖面。它的逻辑是“从可判定到可用”。

**语言风格。** 语言相对清晰直接，强调 automated reasoning 而非新的 quantum model。数学叙事服务于工具目标。对 FTQC 的启发是：如果你的工作涉及 stabilizer tableau、Pauli frame、syndrome history 或 logical operator identities，也可以走“领域记法自动化”的路线，特别是把 fault-tolerance 证明中的重复代数推理自动化。

### 4. RapunSL: Untangling Quantum Computing with Separation, Linear Combination and Mixing

链接：https://doi.org/10.1145/3776648

**解决的问题。** Quantum Separation Logic（QSL）试图让量子程序证明具备局部性：只证明程序影响的 qubits，不反复展开整个全局状态。但已有 QSL 对 superposition 和 measurement-induced mixed states 的处理仍然不够可组合，导致推理规模容易爆炸。

**面临的挑战。** 在经典 separation logic 中，堆分离是结构性局部性；在量子世界里，entanglement 会破坏简单分离。更麻烦的是，superposition 让同一程序分支不能简单分开证明，measurement 又产生概率混合。论文需要定义一种既 sound 又能恢复局部证明能力的逻辑。

**核心思想和技术。** 论文识别出两个量子特有局部性：basis-locality 和 outcome-locality。前者允许把 superposition-state reasoning 化约到 pure basis state reasoning；后者允许把 measurement 产生的 mixed-state reasoning 化约到 pure-state reasoning。为此，RapunSL 引入两个新连接词：linear combination 和 mixing，并与 separation 结合。

**优势与效果。** 新逻辑显著提升了证明可扩展性，能够处理一系列 challenging case studies。它的优势是没有把量子局部性粗暴等同于 classical heap separation，而是承认 superposition/mixing 是新的组合维度，并给出专门逻辑构造。

**写作整体逻辑。** 文章先指出已有 QSL 的 scalability bottleneck，再用两个 locality 概念定位根因；然后引入 connectives，证明 soundness；最后用 case studies 展示推理规模下降。结构很典型：problem diagnosis -> new logical principle -> soundness -> evidence。

**语言风格。** 标题和表述较有修辞性，例如 “Untangling”，但正文逻辑很严谨。它擅长把技术点命名成可传播的概念，如 basis-locality/outcome-locality。对 FTQC 的启发是：FTQC 证明也需要 locality，例如 patch locality、syndrome locality、factory locality、error propagation locality，可以借鉴这种“先命名局部性，再设计逻辑”的写法。

### 5. Qudit Quantum Programming with Projective Cliffords

链接：https://doi.org/10.1145/3776646

**解决的问题。** Clifford operations 在 stabilizer simulation、error correction、compiler IR 中非常核心，但通常以 circuit 或 Pauli tableau 的低层形式出现。程序员难以直接用“Pauli conjugation action”来表达 Clifford 的数学结构，更难在 qudit 维度下保证写出的函数确实对应合法 Clifford。

**面临的挑战。** 一个任意 Pauli 函数不一定来自 Clifford conjugation；它必须保持 Pauli 群结构和 symplectic form。qudit 情况比 qubit 更复杂，尤其偶数维度的 phase encoding 更微妙。论文需要让类型系统捕获这些代数约束，同时保留函数式编程表达力，并能编译成实际 circuit。

**核心思想和技术。** 论文把 projective Clifford 表示为 Pauli 上的函数 \(P \mapsto UPU^\dagger\)，设计 LambdaPC。核心是用线性类型/模块语言表达 Pauli 向量变换，并用类型规则检查 symplectic preservation。它把 Pauli tableau 的 well-formedness 提升为 Curry-Howard 风格的 typing discipline。

**优势与效果。** 用户可以直接编写 projective Clifford 函数，并获得合法性保证和 circuit compilation。论文还通过 stabilizer error-correcting codes case study 说明这种抽象适合容错计算语境。优势是同时覆盖 qubits 和 arbitrary qudits，并为未来 universal Pauli-based programming 铺路。

**写作整体逻辑。** 文章从熟悉的 Clifford/Pauli 背景讲起，展示为什么 conjugation action 比 state action 更适合某些程序；然后逐步引入 qubit examples、qudit complications、calculus、semantics、compilation 和 error-correction case study。它的逻辑是“先用例子建立直觉，再抽象成类型系统”。

**语言风格。** 写作比较友好，例子驱动，数学细节逐步展开。它不是一开始堆定义，而是通过 Hadamard、CNOT、Pauli product 等例子解释类型检查为何必要。对 FTQC 选题非常直接：Clifford/Pauli frame/logical operator transformation 都可以作为类型化编程对象。

### 6. An Expressive Assertion Language for Quantum Programs

链接：https://doi.org/10.1145/3776658

**解决的问题。** Quantum Hoare logic 和 expectation-based reasoning 需要一个足够 expressive 的 assertion language。若断言语言不封闭于 weakest precondition，程序逻辑就无法处理循环和复杂程序的组合推理。

**面临的挑战。** 量子 predicate 本质上是 operator/expectation，而不是经典布尔断言。要在语法层面表达足够多的 quantum predicates，同时还能证明 weakest precondition 可表达，难度很高。带循环的量子程序还要求处理不动点式语义。

**核心思想和技术。** 论文用 generalized Pauli operators 的 quasi-probability distributions 表示 quantum predicates，并借鉴 classical Gödelization 技术，证明对任意程序 \(S\) 和断言 \(\psi\)，其 weakest precondition 仍可在语言中表达。基于此构造 sound and relatively complete quantum Hoare logic。

**优势与效果。** 论文给出了一个表达力强且逻辑上闭合的断言基础，使 expectation-based quantum program verification 不只是针对固定片段。其效果是为 loops 和复杂程序提供理论上完备的推理语言。

**写作整体逻辑。** 文章围绕一个核心问题组织：什么样的量子断言语言足够 expressive？先介绍 expectation reasoning 的需求，再定义断言表示，随后证明 weakest-precondition expressiveness，最后给出 Hoare logic。叙事集中，不分散。

**语言风格。** 理论型、定理驱动，语气稳健。它不像系统论文那样强调 benchmark，而是强调 expressive completeness 和 proof architecture。对 FTQC 的启发是：可以为 fault-tolerant logical programs 设计断言语言，表达 code membership、syndrome constraints、logical error budget 和 resource invariants，并证明对 code switching/magic injection 闭合。

### 7. Proto-Quipper with Dynamic Lifting

链接：https://doi.org/10.1145/3571204

**解决的问题。** Quipper 支持 dynamic lifting：把电路执行时得到的测量结果提升为电路生成时可用的 parameter，从而让后续电路生成依赖测量结果。Proto-Quipper 作为 Quipper 的形式化基础，需要给这个实际语言特性一个严谨语义。

**面临的挑战。** Quantum circuit description language 有两个时间层次：circuit generation time 和 circuit execution time。Dynamic lifting 跨越这两个层次，若不加控制，会破坏 staging discipline 和语义清晰性。论文必须追踪哪些值是 parameter，哪些值是 state，以及 measurement result 何时可以影响生成过程。

**核心思想和技术。** 论文设计 Proto-Quipper-Dyn，用 modal type system 跟踪 dynamic lifting 的使用。它给出 operational semantics 和基于 enriched category theory 的 categorical semantics，并证明类型系统和操作语义相对于 categorical semantics sound。

**优势与效果。** 该工作把 Quipper 中实践上重要但语义上微妙的特性纳入形式化体系，使 interleaving classical and quantum computation 有了可证明基础。它特别适合包含 measurement-feedback 的量子程序。

**写作整体逻辑。** 文章典型地从“现实语言已有功能但理论基础不足”切入；随后解释 phase distinction；再定义语言和类型；接着给语义和 soundness；最后用 dynamic lifting examples 说明必要性。它强调补齐实际语言设计中的理论空白。

**语言风格。** 语义论文风格，概念边界清楚，术语稳定。对 FTQC 的启发非常大：FTQC 也存在多阶段交互，如 syndrome measurement、decoder result、Pauli frame update、feedforward、logical circuit generation。投稿时可以把这些阶段差异作为核心 PL 问题。

### 8. CoqQ: Foundational Verification of Quantum Programs

链接：https://doi.org/10.1145/3571222

**解决的问题。** 量子程序验证需要高可信证明环境，但手工线性代数证明代价高，已有工具的 foundational soundness 往往不够清晰。CoqQ 试图在 Coq 中提供一个既可表达经典量子算法、又有形式化 soundness 的验证框架。

**面临的挑战。** 量子程序语义涉及矩阵、Hilbert 空间、superoperators、测量、概率和 program logic。要在 Coq 中让这些数学结构可用，同时让用户证明不至于过于痛苦，需要在 foundational rigor 和 proof ergonomics 之间平衡。

**核心思想和技术。** CoqQ 深嵌入量子程序语言，构造 program logic，并把 soundness 形式化到 MathComp/MathComp Analysis 这类成熟数学库之上。断言支持 Dirac expressions，证明可利用 local and parallel reasoning 降低工作量。

**优势与效果。** 它的优势是可信度高：逻辑 soundness 不是纸上证明，而是在 proof assistant 中连接到底层数学库。实用性通过多个 literature examples 展示。对于需要高可信验证的量子算法或协议，CoqQ 提供基础设施。

**写作整体逻辑。** 文章先说明为什么需要 foundational verification，再介绍嵌入语言和逻辑；随后强调 soundness formalization；再展示 Dirac notation 和局部推理如何改善可用性；最后用例子证明覆盖面。它的结构是“可信基础 + 证明体验”。

**语言风格。** 工具论文与逻辑论文混合，语气强调可靠性、practicality 和 applicability。对 FTQC 的启发是：如果做 code switching 或 magic-state injection 的 verified semantics，可以选择 mechanized proof 作为差异化优势。

### 9. Qunity: A Unified Language for Quantum and Classical Computing

链接：https://doi.org/10.1145/3571225

**解决的问题。** 很多量子语言像是在 classical host language 上外接 quantum gates，导致量子与经典 constructs 分裂。Qunity 试图设计一种统一语言，让经典程序结构自然推广到量子计算。

**面临的挑战。** 经典 constructs 不能直接搬到量子世界，因为 no-cloning、unitarity、measurement、entanglement 都限制程序结构。语言必须既熟悉又保证 quantum mechanical validity。还要证明它能表达算法并编译到低层 circuit。

**核心思想和技术。** Qunity 用统一语法赋予熟悉 constructs 量子语义：sum types 对应 direct sum of linear operators，exception-like syntax 对应 projective measurements，aliasing 对应 entanglement。它还利用 BQP subroutine theorem，从 irreversible quantum algorithms 构造 reversible subroutines 并 uncompute garbage。

**优势与效果。** 语言让 quantum/classical effects 不再分离，能够表达多个量子算法，并可编译到 OpenQASM。优势在于概念统一，降低“量子 gate assembly”思维负担。

**写作整体逻辑。** 文章先批评“classical + quantum gates bolt-on”的设计，再提出统一语言愿景；随后用多个 constructs 展示量子解释；接着给类型和 denotational semantics；最后说明算法表达和编译可实现。它用 language design 重新组织量子计算概念。

**语言风格。** 语言设计型论文，表达较有宣言感，但技术上落到 semantics 和 compilation。对 FTQC 的启发是：code、syndrome、logical resource 不应只是 backend annotations，而可以成为一等语言 constructs。

### 10. Quantum Circuits Are Just a Phase

链接：https://doi.org/10.1145/3776731

**解决的问题。** 量子程序长期停留在 circuit-as-assembly 层次，即使高级语言的 unitary 部分也常常只是生成门序列。这种低层表达不利于 scalable programming、clarity 和 high-level reasoning。

**面临的挑战。** 要替代 circuit，需要一种足够抽象但仍可编译的 unitary 表达方式。它必须能表达常见算法结构，如 eigendecomposition、controlled unitaries、QFT、Hamiltonian simulation、QSP/QET，同时具有清晰 semantics 和 compiler correctness。

**核心思想和技术。** 论文提出从 “just a phase” 生成 unitaries 的简洁 syntax：用 global phase operation 表达 phase shifts，用 quantum analogue of `if let` 表达 subspace selection 和 pattern matching。该语言把焦点从 gate sequence 转移到 eigenspaces、conjugation 和 controlled constructions。

**优势与效果。** 论文证明语言 universal，能自然表达多个重要算法，并给出 categorical semantics 和 prototype compiler。优势是抽象层次高，但不是不可执行的数学符号；它能落到 circuit。

**写作整体逻辑。** 标题先制造反差：circuits are just a phase。正文从 circuit 低层痛点出发，提出极简 construct；随后用 expressiveness 展示其威力；再补 semantic foundation 和 compiler。它的结构是“强主张 + 小语言 + 大覆盖面”。

**语言风格。** 语言较有野心和可读性，强调 conceptual shift。它适合学习如何写有传播力的 POPL 论文标题和动机。对 FTQC 来说，可以借鉴这种方式提出“fault-tolerant circuits are just typed code transitions / resource effects”之类的高层重构，但必须有定理和 compiler 支撑。

### 11. With a Few Square Roots, Quantum Computing Is as Easy as Pi

链接：https://doi.org/10.1145/3632861

**解决的问题。** Pi 是一个基于 finite types 的 universal classical reversible language。论文关心：在可逆经典计算的语义模型 rig groupoids 上，加入多小的结构就能得到 quantum universality？

**面临的挑战。** Quantum universality 通常通过 gate sets 描述，但论文想给出 equational/categorical characterization。难点是 square roots 不唯一，甚至可能退化，因此必须用合适方程和 nondegeneracy axiom 精确约束新增结构，并证明 soundness/completeness。

**核心思想和技术。** 论文向 rig groupoids 增加两个 maps 和三个 equations：一个对应 unit object 上 identity morphism 的 8th root，另一个对应 \(1+1\) 上 symmetry 的 square root，并用 nondegeneracy 连接 Hadamard 的 Euler decomposition。由此构造 Pi 的量子扩展，并证明对多种 gate set 的 sound and complete equational theory。

**优势与效果。** 它从极小扩展获得 computational universality，并提供等式理论。这种结果把“量子比经典多什么”说得非常精确，具有理论美感和解释力。

**写作整体逻辑。** 文章先回到经典可逆语言 Pi，再提出“只加少量 square roots 是否足够”的问题；随后构造语义扩展、语言扩展和 equational theory；最后把结果落实到 Clifford、Clifford+T 等 gate sets。它的叙事是 minimal extension -> universality -> completeness。

**语言风格。** 标题轻松，正文理论密度高。它擅长用一个简单 hook 承载复杂范畴语义。对 FTQC 的启发是：可以问“从 fault-tolerant Clifford fragment 到 universal FTQC，最小的资源/construct 是什么”，并给出 equational/type-theoretic characterization。

### 12. Hadamard-Pi: Equational Quantum Programming

链接：https://doi.org/10.1145/3776647

**解决的问题。** 在标准电路模型中，在 universal classical reversible gates 上加入 Hadamard 就能得到 universal quantum computation 的关键能力之一，但 Hadamard 添加后究竟带来怎样的 computational behavior 并未被完全刻画。

**面临的挑战。** 论文要把“加一个 Hadamard primitive”从 gate-set 事实提升为 programming language 和 equational theory。它必须给出 sound and complete categorical semantics，还要为相关矩阵群提供 finite presentation 和 synthesis algorithm。

**核心思想和技术。** 论文扩展 classical reversible language Pi，加入单一 Hadamard primitive。其语义由纯等式理论刻画；completeness 通过对 \(\mathbb{Z}[1/\sqrt{2}]\) 上正交矩阵群的新 finite presentation 和 synthesis algorithm 建立。

**优势与效果。** 结果精确说明 Hadamard 这一 basis-changing gate 的表达能力，并给出可合成的等式语言。优势是非常聚焦：一个 primitive，一个完整理论。

**写作整体逻辑。** 文章沿着“经典可逆基底 + 一个量子 primitive”的主线展开。它先用标准量子计算事实建立动机，再指出行为刻画缺口，随后给语言、语义、presentation 和 synthesis。整体非常紧凑。

**语言风格。** 形式化、克制、定理导向。相比 “Quantum Circuits Are Just a Phase” 的广覆盖，这篇更像一把窄而深的刀。对 FTQC 的启发是：可以围绕一个 FTQC primitive，如 `CodeSwitch`、`TFactory`、`CCZResource`，做完整 equational/type-theoretic characterization。

### 13. Quantum Bisimilarity via Barbs and Contexts

链接：https://doi.org/10.1145/3632885

**解决的问题。** 量子过程演算已有多个 proposal，但对 behavioral equivalence 的定义没有统一标准，特别是 context/observer 对 quantum values 能观察什么并不清楚。若 observer 太强，语义可能违反量子理论。

**面临的挑战。** 在经典 process calculi 中，context 可以通过交互观察进程行为；但量子状态不可克隆、测量会扰动状态，context 不能拥有不受物理约束的 nondeterministic power。论文需要找到既保留 classical nondeterminism 表达力，又不允许 context 非物理观察 quantum values 的 bisimilarity。

**核心思想和技术。** 论文提出 Linear Quantum CCS（lqCCS），结合 asynchronous communication 和 linearity，确保每个 qubit 只被发送一次，并精确指定哪些 qubits 与 context 交互。它证明一般 context 的 observational power 与量子理论不兼容，然后 refined operational semantics，限制 context 做不可实现的 nondeterministic choices。

**优势与效果。** 新 bisimilarity 更符合量子物理：它把 quantum state indistinguishability 提升到 process distribution 层面，同时保留基于 classical information 的 nondeterminism。论文价值在于指出一个常见语义直觉在量子场景下是错的，并给出修复。

**写作整体逻辑。** 文章是“反例/不相容性 -> 约束 observer -> 新等价关系”的结构。它先让读者接受 process calculus 的必要性，再展示一般 context 过强，最后给 refined semantics 和性质证明。

**语言风格。** 论证风格偏语义学，强调 conceptual correctness。语言中有清晰的批判性判断，例如 context power incompatible with quantum theory。对 FTQC 的启发是：decoder、controller、runtime scheduler 也可能被赋予过强语义能力；论文可以通过类似方式界定 physically realizable control。

### 14. Verifying Quantum Circuits with Level-Synchronized Tree Automata

链接：https://doi.org/10.1145/3704868

**解决的问题。** 量子电路验证通常面临指数维状态空间。已有 symbolic representation 或 simulation 方法难以同时做到表达力、闭包性质、可判定性和效率。特别是 parameterized verification 超出很多工具能力。

**面临的挑战。** 需要一种能紧凑表示 quantum state sets 的符号模型，并支持 gate operations 后的状态更新、集合运算、emptiness/inclusion 等验证所需操作。模型太弱则不能表达实际电路；太强则不可判定或算法复杂度过高。

**核心思想和技术。** 论文提出 level-synchronized tree automata（LSTAs）。与普通 tree automata 相比，LSTA 在 transitions 上标注 choices，并用这些 choices 同步子树。基于 LSTA，论文构造 quantum circuit symbolic verification algorithm，支持 closure under union/intersection 和 decidable emptiness/inclusion。

**优势与效果。** 对支持的 gate operations，复杂度至多 quadratic，相比早期 tree-automata 方法的 exponential worst-case 有显著改善。C++ 实现与三个 symbolic verifiers、两个 simulators 比较，能解决更大规模问题。它还显示 LSTA 适合 parameterized verification。

**写作整体逻辑。** 文章采用算法论文结构：先说明验证瓶颈；然后介绍新自动机模型及其闭包/判定性质；再给 gate semantics 和 verification algorithm；最后通过实现和 benchmark 展示规模优势。

**语言风格。** 形式模型和实验结果并重，表述清楚，强调 automated、efficient、fully symbolic。对 FTQC 的启发是：syndrome extraction、distillation factory、code-switching protocol 都是参数化电路族，可以考虑类似“有限表示无限族”的验证路线。

### 15. SimuQ: A Framework for Programming Quantum Hamiltonian Simulation with Analog Compilation

链接：https://doi.org/10.1145/3632923

**解决的问题。** Hamiltonian simulation 是量子计算重要应用，但 analog quantum simulators 的编程接口高度设备相关。用户难以用统一语言描述目标 Hamiltonian，硬件提供者也缺少统一方式表达设备的 Hamiltonian-level capability。

**面临的挑战。** 模拟目标和硬件可实现交互之间存在巨大语义鸿沟。不同平台（IBM superconducting、QuEra neutral atom、IonQ trapped ion）native operations 不同；compiler 需要把 high-level Hamiltonian 映射到 pulse schedules。抽象必须同时服务用户和硬件提供者。

**核心思想和技术。** SimuQ 设计两端语言：用户用 Hamiltonian Modeling Language 描述目标系统；硬件提供者用 AAIS Specification Language 描述 abstract analog instruction set。中间通过 solver-based compilation 生成 pulse-level executable schedules。

**优势与效果。** SimuQ 是一个完整框架，能在多种硬件平台上演示 Hamiltonian simulation 编译，并建立 benchmark。优势是把 analog programmability 变成可声明、可编译的接口，而不是每个平台重写程序。

**写作整体逻辑。** 文章从 NISQ/analog simulation 的实际机会切入，再指出 interface 缺失；随后提出前端语言、后端 AAIS、solver-based compiler；最后用真实或接近真实设备展示。它是典型“领域框架 + DSL + 编译器 + 实验”。

**语言风格。** 系统论文风格，强调 framework、heterogeneous devices、programmability。对 FTQC 的启发是：可以为 FTQC 后端设计类似 AAIS 的 `Fault-Tolerant Capability Specification Language`，描述 code、switch、factory、decoder 和 physical constraints。

### 16. Enriched Presheaf Model of Quantum FPC

链接：https://doi.org/10.1145/3632855

**解决的问题。** Selinger 的 superoperator model 已能处理一阶量子语言并给出 full abstraction，但高阶程序和递归类型需要更强语义结构。论文目标是为带 recursive types 的 Quantum FPC 建立 fully abstract model。

**面临的挑战。** 高阶量子语言要同时处理 linear logic、classical control、quantum effects、递归类型和概率/测量。普通 superoperator category 不足以直接支持高阶函数和递归。语义模型必须既有足够结构解释语言，又保持可证明 full abstraction。

**核心思想和技术。** 论文使用 superoperators 上的 enriched presheaves，或等价地使用 superoperator modules。该 enriched presheaf category 可作为 intuitionistic linear logic 的模型，并通过 bi-orthogonality construction 得到 classical linear logic model。模型中的 morphism 可表示为 completely positive maps 的矩阵，并具备 \(\omega\)-CPO enrichment 以解释递归类型。

**优势与效果。** 论文给出 Quantum FPC 的 fully abstract model，解决高阶量子 lambda calculus 的语义基础问题。优势是继承 Selinger model 的良好性质，同时支持更丰富语言特性。

**写作整体逻辑。** 文章先回顾 Selinger model 的成就和限制；然后引入 enriched presheaf construction；接着证明模型支持所需逻辑结构和 recursive types；最后给 Quantum FPC 并证明 full abstraction。它是纯语义贡献的典型 POPL 写法。

**语言风格。** 高度理论化，范畴语义术语密集，语言克制。它对 FTQC 的启发不是直接技术，而是提醒：如果你能为“encoded/noisy/fault-tolerant computation”建立新的 fully abstract 或 adequacy model，会有 POPL 理论价值，但门槛很高。

### 17. Qurts: Automatic Quantum Uncomputation by Affine Types with Lifetime

链接：https://doi.org/10.1145/3704842

**解决的问题。** Quantum uncomputation 允许丢弃中间值而不丢失量子信息，并让 compiler 重用资源。量子信息通常需要线性使用，但 automatic uncomputation 又希望程序员能在一定范围内 affine 地使用值。已有语言常以 ad hoc 方式处理这个线性/仿射之间的微妙地带。

**面临的挑战。** 直接允许 discard 会违反 unitarity；严格线性又让程序难写、资源不可复用。论文需要找到一种类型机制，在值生命周期内允许 affine 使用，但在生命周期边界恢复线性约束，并给出不依赖具体 uncomputation strategy 的语义。

**核心思想和技术。** Qurts 把 Rust lifetime discipline 扩展到量子类型。类型按 lifetimes 参数化：量子值在 lifetime 内可 affine 使用，而离开 lifetime 后必须满足线性限制。论文给出两种 operational semantics：一种基于 classical simulation，一种独立于特定 uncomputation strategy。

**优势与效果。** 它把 automatic uncomputation 从语言特例变成统一类型原则，既提升程序可写性，也保留资源安全。Rust 类比让读者容易理解 lifetime 的作用。

**写作整体逻辑。** 文章从 uncomputation 的程序员痛点出发，解释线性和仿射之间的冲突；然后借鉴 Rust lifetimes 给出类型系统；随后给语义和性质；最后说明该 discipline 如何支持 automatic uncomputation。

**语言风格。** PL 社区友好，善用 Rust 作为桥梁。语言不像纯量子信息论文，而是典型类型系统论文。对 FTQC 的启发是：magic states、logical patches、ancilla blocks、syndrome resources 都可借鉴 lifetime/affine/linear 资源管理。

### 18. A Case for Synthesis of Recursive Quantum Unitary Programs

链接：https://doi.org/10.1145/3632901

**解决的问题。** 参数化量子算法常以递归程序生成一族 unitary circuits，手写和验证都困难。论文希望启动 recursive quantum unitary programs 的自动综合研究，让工具从 specification 合成程序。

**面临的挑战。** 量子程序综合同时涉及 unitary correctness、递归结构、参数化电路族和低层量子细节。搜索空间大，语义约束强。论文需要设计一个足够受控的 inductive quantum language 和 specification logic，使问题可编码到 SMT。

**核心思想和技术。** QSynth 包括新的 inductive quantum programming language、specification、sound logic，以及将 reasoning procedure 编码成 SMT instances 的方法。它利用 SMT solver 合成递归量子程序。

**优势与效果。** QSynth 成功合成 10 个程序，包括 quantum arithmetic、eigenvalue inversion、teleportation 和 QFT，并能转译到 Q#、Qiskit、Braket 等平台。优势是把“写量子递归程序”转为可自动化任务。

**写作整体逻辑。** 标题中 “A Case for” 明确表示开辟方向。文章先说明手写量子程序困难，再定义合成问题；随后给语言和逻辑；再给 SMT encoding；最后用多个案例证明值得研究。它是“提出一个新 PL 问题领域”的写法。

**语言风格。** 问题倡议与技术实现结合，语言强调 first framework、initiate the study。对 FTQC 的启发是：可以提出 “synthesis of fault-tolerant code-switch schedules / factory protocols / lattice-surgery layouts” 作为新问题，但必须给出 formal spec 和 solver/algorithm。

### 19. Parameterized Verification of Quantum Circuits

链接：https://doi.org/10.1145/3776712

**解决的问题。** 很多量子程序不是固定电路，而是根据输入规模生成电路族。验证单个规模不能证明一般正确性。论文要验证 parameterized quantum programs 的 relational properties，如 input-output correctness 和 equivalence。

**面临的挑战。** 参数化电路族代表无限多个电路，状态空间随规模指数增长。验证需要紧凑且精确地表示无限量子状态族，并能组合 gate semantics。还需要可判定 inclusion/equivalence procedures。

**核心思想和技术。** 论文提出 synchronized weighted tree automata（SWTAs），紧凑表示参数化程序生成的无限量子状态族。再引入 transducers 表示 quantum gate semantics，并开发 composition algorithms，把验证化约为 SWTA 之间的 functional inclusion 或 equivalence checking。

**优势与效果。** 这是首个 fully automatic framework 用于此类 relational verification。实现能在 milliseconds 到 seconds 内验证多种代表性参数化量子程序，兼具表达力和效率。

**写作整体逻辑。** 文章与 LSTA 论文一脉相承，但更强调参数化和 relational properties。结构为：参数化验证需求 -> SWTA 模型 -> transducer gate semantics -> decision procedure -> implementation evaluation。

**语言风格。** 自动验证论文风格，术语精确，强调 first fully automatic。对 FTQC 极有启发：code distance、syndrome rounds、factory levels、logical circuit size 都是参数，若能验证“任意距离/任意轮数”的 FTQC gadget，会非常 POPL。

### 20. Linear and Non-linear Relational Analyses for Quantum Program Optimization

链接：https://doi.org/10.1145/3704873

**解决的问题。** Phase folding 是降低 quantum circuits 中高成本 gates 的重要优化，但传统 formulation 依赖精确线性代数表示，通常限制在 straight-line circuits 或 basic blocks，难以处理带 classical control flow、loops 和 procedure calls 的量子程序。

**面临的挑战。** 真正的量子程序有复杂控制流，优化需要跨循环和过程推导不变量。若仍用低层电路代数表示，难以应用 classical static analysis 成熟技术。论文需要把量子优化转换到适合抽象解释/关系分析的形式。

**核心思想和技术。** 论文把 phase folding 重新表述为 affine relation analysis，从而可直接利用经典 affine relation 技术处理复杂程序。进一步，它展示可替换为 non-linear relational domains，以处理 classical arithmetic 参与的 circuits。对 Clifford+T 等线性 gate sets，论文用 sum-over-paths 提取 straight-line circuits 的精确 symbolic transition relations。

**优势与效果。** 该方法能生成并利用非平凡 loop invariants 做 quantum program optimization，且实现一些过去只能手工完成的优化。优势是把量子编译优化纳入经典程序分析框架，提升可扩展性。

**写作整体逻辑。** 文章先定位一个真实 compiler optimization 的适用范围缺陷；然后给出关键 reframing：phase folding = relational analysis；再扩展到 non-linear domain 和 sum-over-paths；最后用实验说明优化能力。它是很强的 POPL 模板。

**语言风格。** 静态分析论文风格，强调 recasting、domains、invariants、precision。对 FTQC 的启发最直接：code-switch minimization、factory scheduling、logical error budget propagation 都可以被重述为静态分析问题。

### 21. Flexible Type-Based Resource Estimation in Quantum Circuit Description Languages

链接：https://doi.org/10.1145/3704883

**解决的问题。** Quipper 这类 circuit description language 能生成大规模电路，但程序员和 compiler 需要在生成前知道 circuit 的 size upper bounds，如 width、depth、gate count，甚至只统计某些 wire types 或 gate kinds。已有方法灵活性不足。

**面临的挑战。** 资源度量很多，且同一程序可按不同 metric 解释。类型系统需要表达 generic arithmetic expressions，并允许这些 expressions 的 operators 随 target metric 改变解释。还要在 presence of higher-order circuit generation 中证明 resource upper bounds 正确。

**核心思想和技术。** 论文为 Quipper 设计 type system，用 effects 和 refinement types 推导生成电路大小上界。关键是 indexed arithmetic expressions：同一索引表达式可按 width、depth、gate count 或更细粒度 metric 解释。正确性通过 logical predicates 在合理 metric 假设下证明。工具 QuRA 自动推断紧上界。

**优势与效果。** 框架高度灵活，支持多种资源指标和变体，且在许多例子中能自动推断 tight bounds。它把资源分析从后端统计提前到类型层。

**写作整体逻辑。** 文章从 circuit generation 的资源不可见性切入；然后设计 effect/refinement/indexed type system；再给 correctness proof；最后用 QuRA 工具评估自动化能力。它非常贴近 POPL 对“类型系统解决实际编程问题”的期待。

**语言风格。** 类型系统和资源分析风格，语言准确、工程目标明确。对 FTQC 投稿最关键：logical-qubit count、code distance、T/CCZ factory throughput、code switch count、decoder latency、physical qubit-rounds 都可以成为类似的 flexible metrics。

## 跨论文写作范式

### 范式一：把低层量子对象提升为语言抽象

代表论文：Qudit Projective Cliffords、Quantum Circuits Are Just a Phase、Qunity、SimuQ。

共同逻辑是：低层 circuit/tableau/pulse/Dirac expression 虽然能表达计算，但不利于组合和推理。论文通过语言或 DSL 把结构暴露出来，再给语义和编译。

适合 FTQC 的转化：把 code、logical patch、Pauli frame、syndrome history、magic-state factory、code switch 从 backend data structures 提升为 typed programming constructs。

### 范式二：用类型/效果系统管理量子资源

代表论文：Qurts、Flexible Type-Based Resource Estimation、Indexed Monads and Resource Analysis。

共同逻辑是：量子资源不能随便复制/丢弃，生成电路的成本也不能事后才知道。类型系统适合在程序层面表达使用纪律和上界。

适合 FTQC 的转化：magic state 是线性/仿射消耗资源；factory 是有 throughput 和 failure model 的资源；logical qubit code 是 typestate；code distance 是 refinement index；logical error budget 是 quantitative effect。

### 范式三：用逻辑恢复局部推理

代表论文：RapunSL、Expressive Assertion Language、CoqQ。

共同逻辑是：量子全局态太大，必须通过合适断言、分离原则或 proof assistant 结构恢复 compositional reasoning。

适合 FTQC 的转化：FTQC 的 locality 包括 patch locality、stabilizer locality、syndrome locality、fault-propagation locality、factory locality。可设计 separation logic 或 assertion language，证明 code switching / injection / lattice surgery 保持局部规格。

### 范式四：用自动机/SMT/rewriting 让验证自动化

代表论文：LSTA、Parameterized Verification、Dirac Notation、QSynth。

共同逻辑是：手工证明量子电路族很难，必须找到一个有限符号表示或可判定理论，再接入工具。

适合 FTQC 的转化：FTQC gadget 往往是参数化电路族，尤其按 code distance、rounds、factory level 参数化。可用自动机、rewriting、SMT 或 abstract interpretation 自动验证 syndrome schedule、code-switch circuit、factory protocol。

### 范式五：负面发现 + 纪律修复

代表论文：Quantum Bisimilarity via Barbs and Contexts。

共同逻辑是：先说明一个看似自然的语义/观察者/编译器假设其实不物理或不 sound，然后提出受限但足够表达的 disciplined semantics。

适合 FTQC 的转化：naive runtime feedback、decoder oracle、postselection、magic-pool scheduling、logical frame update 都可能隐藏过强假设。指出并修复这种假设，可能形成很好的 POPL 叙事。

## 近期 FTQC 方向与 POPL 机会

### Magic-state preparation 正在从单一 distillation 变为协议族

近期相关工作包括：

- Constant-overhead magic state distillation：用 asymptotically good codes 实现 \(O(1)\) overhead。https://arxiv.org/abs/2408.07764
- Magic state cultivation：把 T state 逐步 grow 到高可靠度，成本接近同可靠度 lattice-surgery CNOT。https://arxiv.org/abs/2409.17595
- Superconducting processor 上的 cultivation 实验：包含 code switching into surface code 和 fidelity bounding。https://arxiv.org/abs/2512.13908
- Zero-level distillation：在 physical level 用 Steane-code-style protocol 准备 logical magic state。https://arxiv.org/abs/2403.03991
- Unfolded distillation：针对 biased-noise qubits 的低成本 magic state preparation。https://arxiv.org/abs/2507.12511
- MagicPool：处理 magic state distillation failure 对并行执行造成的 runtime delay。https://arxiv.org/abs/2407.07394

POPL 机会：不要只比较协议常数，而是设计一个 magic-resource calculus，把 distillation/cultivation/zero-level/unfolded protocols 统一为带 precondition、failure model、latency、throughput、code conversion 的资源效果。

### Code switching 正在成为 universal FTQC 的主路线之一

近期相关工作包括：

- Near-term code switching protocols：在不同 color code 之间切换以获得 universal gate set。https://doi.org/10.1103/PRXQuantum.5.020345
- Experimental fault-tolerant code switching：7-qubit color code 与 10-qubit code 之间实验切换。https://arxiv.org/abs/2403.13732
- Single-shot universality via code switching：在高率 HGP codes 间切换，避免 magic-state distillation。https://arxiv.org/abs/2510.08552
- Minimizing code switching operations：把 code switch minimization 化约为 min-cut。https://arxiv.org/abs/2512.04170
- Weakly fault-tolerant code switching in [[8,3,2]] code。https://arxiv.org/abs/2603.15610

POPL 机会：code switching 本质上就是 typestate transition。一个 typed IR 可以把 `Qubit[CodeA] -> Qubit[CodeB]` 作为受约束转换，并跟踪 logical basis、distance、allowed gates、fault model、resource/error effects。

### QLDPC 和 constant-overhead 方向需要更强编译抽象

相关工作包括：

- Polylog-time and constant-space overhead FTQC with QLDPC codes。https://arxiv.org/abs/2411.03683
- Qudit asymptotically good codes for magic state distillation。https://arxiv.org/abs/2512.21874
- Error-structure-tailored early FTQC。https://arxiv.org/abs/2511.19983

POPL 机会：这些工作通常有复杂 compilation stages、register partitioning、auxiliary states、decoders 和 resource assumptions。PL 贡献可以是把这些 stage 变成形式化 compiler pipeline，并证明 stage composition preserves logical semantics and fault-tolerance bounds。

## 推荐 POPL 2027 选题

### 首选题目

**A Code-Indexed Resource Calculus for Universal Fault-Tolerant Quantum Programs**

或更工程一些：

**Typed Compilation of Code Switching and Magic-State Resources for Fault-Tolerant Quantum Programs**

### 核心问题

当前 FTQC 软件栈通常把 algorithmic circuit 先降到 Clifford+T，再由后端 ad hoc 选择 code switching、magic state factories、cultivation、distillation、lattice surgery 或 Pauli frame update。这个流程的问题是：程序层面看不到资源和容错假设，优化 pass 很难证明不会破坏 logical correctness 或 error budget。

### 核心技术路线

设计一个小语言或 IR：

- `Q[c, d]` 表示 code `c`、distance `d` 下的 logical qubit。
- gate capability 以约束表示，例如 `Transversal H c`、`Transversal CNOT c`、`Inject T c`、`Switch c1 c2`。
- code switching 是 typed transition，而不是裸 circuit macro。
- magic states 是 linear/affine resources，例如 `TState[e]`、`CCZState[e]`。
- factories/cultivation/distillation 是 resource providers，带 throughput、failure probability、latency、space-time volume。
- decoder/feedforward 是 indexed effect，记录 classical latency 和可用信息阶段。
- resource effect algebra 聚合 switch count、factory demand、physical qubit-rounds、logical error budget。

### 可证明结果

最低应有：

- Type preservation：code-indexed logical program 的类型状态转换良构。
- Denotational soundness：擦除 code/resource annotations 后仍实现目标 logical unitary/channel。
- Fault-tolerance soundness：well-typed switch/injection/factory use 满足给定 local stochastic 或 adversarial fault model 的局部条件。
- Resource soundness：类型推导出的 resource/error bounds 是后端 cost model 的上界。
- Optimization correctness：code-switch minimization、magic-pool scheduling 或 factory selection 不改变语义且不违反资源效果。

### 实现与评估

建议实现一个 prototype compiler：

- 输入：小型 logical circuit language 或 OpenQASM-like IR。
- 后端：至少两个 code families/protocols，例如 surface code + color/Steane code switching，或 surface-code cultivation + magic-state factory。
- 优化：code switch placement、magic resource pooling、distance/resource inference。
- benchmark：QFT、phase estimation fragment、Hamiltonian simulation kernel、arithmetic circuits、T/CCZ-heavy workloads。

### 为什么适合 POPL

它能同时连接 21 篇 POPL 量子论文中的多条主线：

- 语言抽象：像 Qunity、Phase language、Qudit Clifford。
- 类型与资源：像 Qurts、Flexible Resource Estimation、Indexed Monads。
- 自动验证：像 LSTA、SWTA、Dirac rewriting。
- 编译器生成/后端多样性：像 QMR compiler generation、SimuQ。
- 逻辑与局部性：像 RapunSL、Expressive Assertion Language。

这不是单纯 FTQC 物理论文，而是一个“让 FTQC 变成可编程、可验证、可优化软件对象”的 POPL 论文。

## 备选选题

### 备选一：Magic-state factory 的概率资源类型系统

研究 magic state distillation/cultivation/factory failure 对程序执行的影响。核心贡献可以是一个 probabilistic linear resource calculus，静态保证 expected latency、pool size、failure probability 和 resource budget。

优势：紧贴 MagicPool、cultivation、zero-level/unfolded distillation。

风险：如果没有强类型理论或语义定理，容易被看成 architecture scheduling。

### 备选二：Code switching 的 verified synthesis

给定 logical program 和 code/gate/switch capability library，自动合成 code-switch schedule，并证明语义正确和 resource bound。

优势：结合 QSynth、QMR compiler generation、min-cut code-switch optimization。

风险：需要比 min-cut paper 更强的 PL abstraction，否则像算法工程。

### 备选三：FTQC patch separation logic

为 surface-code patches、lattice surgery、code switching 和 factory regions 设计 separation logic，支持局部证明和 frame rule。

优势：承接 RapunSL，主题非常 POPL。

风险：需要真实 FTQC case studies，否则容易过于抽象。

### 备选四：Fault-tolerant Clifford+phi typed language

绕开全部 Clifford+T/T-state 编译，把 continuous-angle logical rotations 作为 first-class operations，并用 backend capability/fault model 判断哪些旋转可直接容错执行。

优势：呼应 error-structure-tailored early FTQC，题目新。

风险：物理假设较强，POPL 读者可能要求更通用的语言原则。

## 写作建议

### Introduction 应该怎样写

不要从“量子计算很重要”开始。应该从软件痛点开始：

> Universal fault-tolerant quantum computation is no longer a single compilation target. Modern proposals combine code switching, magic-state cultivation, distillation, transversal gates, Pauli-frame tracking, decoders, and hardware-specific constraints. Yet today these choices are mostly encoded in backend-specific scripts and informal resource spreadsheets, making correctness and resource assumptions non-compositional.

然后用一个小例子展示：同一 logical T/CCZ-heavy program 在不同 code/factory choices 下有不同资源效果；naive compiler pass 会破坏 code assumptions 或造成 factory stalls。

### 技术主体应该怎样组织

推荐结构：

1. 一个 running example：同一程序需要 Clifford gates、non-Clifford resources、code switching 和 feedforward。
2. Core calculus：types, effects, resources。
3. Operational/denotational semantics：logical meaning + backend trace。
4. Type system：code capabilities and resource effects。
5. Soundness theorems。
6. Optimizations：switch minimization / factory scheduling / resource inference。
7. Prototype and evaluation。
8. Relation to POPL quantum work and FTQC protocols。

### 语言风格建议

POPL 论文需要让 PL 读者看懂贡献，而不是默认他们懂 FTQC。建议每个物理概念都用软件类比引入：

- Code switching = typestate transition with a nontrivial representation invariant.
- Magic state = linear capability enabling a non-Clifford operation.
- Factory = resource provider with stochastic latency and throughput.
- Pauli frame = symbolic runtime state maintained by classical control.
- Decoder = effectful classical oracle with latency and fault model assumptions.

同时，不要把论文写成 survey。FTQC 最新工作只能做动机和后端实例；主贡献必须是一个新抽象和定理。

## 简短结论

如果以 POPL 2027 为目标，最稳妥的路线是把 universal FTQC 中最混乱的软件边界：code switching + magic resources + resource/error accounting，整理为一个类型化、效果化、可优化的 compiler IR。它既有明确现实需求，也能自然产出 POPL 需要的语言设计、静态保证、语义定理和工具评估。

最不建议的路线是只提出新 distillation protocol 或只做 resource spreadsheet。那些可以支撑论文动机，但不能成为 POPL 主贡献。

