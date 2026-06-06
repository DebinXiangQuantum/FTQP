import Std

namespace FTQP

inductive Code where
  | surfaceD5
  | steane3
  | tetra15
  | qldpc12
deriving DecidableEq, Repr

inductive Gate where
  | H
  | S
  | CNOT
  | T
  | CCZ
deriving DecidableEq, Repr

inductive Mode where
  | state
  | observable
deriving DecidableEq, Repr

inductive ResKind where
  | tState
  | cczState
  | bellPair
deriving DecidableEq, Repr

inductive CertLevel where
  | checked
  | certified
  | assumed
deriving DecidableEq, Repr

structure Policy where
  allowAssumed : Bool
deriving DecidableEq, Repr

namespace Policy

def exploratory : Policy := { allowAssumed := true }
def strict : Policy := { allowAssumed := false }

end Policy

def certAllowed (π : Policy) : CertLevel -> Bool
  | CertLevel.checked => true
  | CertLevel.certified => true
  | CertLevel.assumed => π.allowAssumed

def supportsGate : Code -> Gate -> Bool
  | Code.surfaceD5, Gate.H => true
  | Code.surfaceD5, Gate.S => true
  | Code.steane3, Gate.H => true
  | Code.steane3, Gate.S => true
  | Code.steane3, Gate.CNOT => true
  | Code.tetra15, Gate.CNOT => true
  | Code.tetra15, Gate.T => true
  | Code.qldpc12, Gate.H => true
  | Code.qldpc12, Gate.S => true
  | Code.qldpc12, Gate.CNOT => true
  | Code.qldpc12, Gate.T => true
  | _, _ => false

def gateCert : Code -> Gate -> CertLevel
  | Code.surfaceD5, Gate.H => CertLevel.checked
  | Code.surfaceD5, Gate.S => CertLevel.checked
  | Code.steane3, Gate.H => CertLevel.checked
  | Code.steane3, Gate.S => CertLevel.checked
  | Code.steane3, Gate.CNOT => CertLevel.checked
  | Code.tetra15, Gate.CNOT => CertLevel.certified
  | Code.tetra15, Gate.T => CertLevel.certified
  | Code.qldpc12, _ => CertLevel.assumed
  | _, _ => CertLevel.assumed

def switchExists : Code -> Code -> Bool
  | Code.steane3, Code.tetra15 => true
  | Code.tetra15, Code.steane3 => true
  | Code.surfaceD5, Code.steane3 => true
  | Code.steane3, Code.surfaceD5 => true
  | Code.surfaceD5, Code.tetra15 => true
  | Code.tetra15, Code.surfaceD5 => true
  | Code.surfaceD5, Code.qldpc12 => true
  | Code.qldpc12, Code.surfaceD5 => true
  | _, _ => false

def switchCert : Code -> Code -> CertLevel
  | Code.steane3, Code.tetra15 => CertLevel.certified
  | Code.tetra15, Code.steane3 => CertLevel.certified
  | Code.surfaceD5, Code.steane3 => CertLevel.assumed
  | Code.steane3, Code.surfaceD5 => CertLevel.assumed
  | Code.surfaceD5, Code.tetra15 => CertLevel.assumed
  | Code.tetra15, Code.surfaceD5 => CertLevel.assumed
  | Code.surfaceD5, Code.qldpc12 => CertLevel.assumed
  | Code.qldpc12, Code.surfaceD5 => CertLevel.assumed
  | _, _ => CertLevel.assumed

structure QTy where
  code : Code
  distance : Nat
  mode : Mode
deriving DecidableEq, Repr

structure Effect where
  err : Nat
  fail : Nat
  space : Nat
  time : Nat
  factories : Nat
  switches : Nat
deriving DecidableEq, Repr

namespace Effect

def zero : Effect :=
  { err := 0, fail := 0, space := 0, time := 0, factories := 0, switches := 0 }

def seq (a b : Effect) : Effect :=
  { err := a.err + b.err
    fail := a.fail + b.fail
    space := max a.space b.space
    time := a.time + b.time
    factories := a.factories + b.factories
    switches := a.switches + b.switches }

def branch (a b : Effect) : Effect :=
  { err := max a.err b.err
    fail := max a.fail b.fail
    space := max a.space b.space
    time := max a.time b.time
    factories := max a.factories b.factories
    switches := max a.switches b.switches }

def Le (a b : Effect) : Prop :=
  a.err ≤ b.err ∧
  a.fail ≤ b.fail ∧
  a.space ≤ b.space ∧
  a.time ≤ b.time ∧
  a.factories ≤ b.factories ∧
  a.switches ≤ b.switches

theorem seq_left_bound (a b : Effect) : Le a (seq a b) := by
  unfold Le seq
  constructor
  · exact Nat.le_add_right a.err b.err
  constructor
  · exact Nat.le_add_right a.fail b.fail
  constructor
  · exact Nat.le_max_left a.space b.space
  constructor
  · exact Nat.le_add_right a.time b.time
  constructor
  · exact Nat.le_add_right a.factories b.factories
  · exact Nat.le_add_right a.switches b.switches

theorem seq_right_bound (a b : Effect) : Le b (seq a b) := by
  unfold Le seq
  constructor
  · exact Nat.le_add_left b.err a.err
  constructor
  · exact Nat.le_add_left b.fail a.fail
  constructor
  · exact Nat.le_max_right a.space b.space
  constructor
  · exact Nat.le_add_left b.time a.time
  constructor
  · exact Nat.le_add_left b.factories a.factories
  · exact Nat.le_add_left b.switches a.switches

theorem branch_left_bound (a b : Effect) : Le a (branch a b) := by
  unfold Le branch
  constructor
  · exact Nat.le_max_left a.err b.err
  constructor
  · exact Nat.le_max_left a.fail b.fail
  constructor
  · exact Nat.le_max_left a.space b.space
  constructor
  · exact Nat.le_max_left a.time b.time
  constructor
  · exact Nat.le_max_left a.factories b.factories
  · exact Nat.le_max_left a.switches b.switches

theorem branch_right_bound (a b : Effect) : Le b (branch a b) := by
  unfold Le branch
  constructor
  · exact Nat.le_max_right a.err b.err
  constructor
  · exact Nat.le_max_right a.fail b.fail
  constructor
  · exact Nat.le_max_right a.space b.space
  constructor
  · exact Nat.le_max_right a.time b.time
  constructor
  · exact Nat.le_max_right a.factories b.factories
  · exact Nat.le_max_right a.switches b.switches

theorem seq_err_exact (a b : Effect) :
    (seq a b).err = a.err + b.err := rfl

theorem seq_time_exact (a b : Effect) :
    (seq a b).time = a.time + b.time := rfl

end Effect

abbrev RCtx := Nat -> Bool

def emptyResources : RCtx := fun _ => false

def put (ρ : RCtx) (r : Nat) : RCtx :=
  fun x => if x = r then true else ρ x

def take (ρ : RCtx) (r : Nat) : RCtx :=
  fun x => if x = r then false else ρ x

@[simp] theorem put_self (ρ : RCtx) (r : Nat) : put ρ r r = true := by
  simp [put]

@[simp] theorem take_self (ρ : RCtx) (r : Nat) : take ρ r r = false := by
  simp [take]

theorem put_ne (ρ : RCtx) {x r : Nat} (h : x ≠ r) :
    put ρ r x = ρ x := by
  simp [put, h]

theorem take_ne (ρ : RCtx) {x r : Nat} (h : x ≠ r) :
    take ρ r x = ρ x := by
  simp [take, h]

inductive Prim where
  | direct (code : Code) (gate : Gate) (q : Nat)
  | switch (source : Code) (target : Code) (q : Nat)
  | produce (r : Nat) (kind : ResKind)
  | consume (r : Nat) (kind : ResKind) (gate : Gate) (q : Nat)
  | measureL (targetBit : Nat) (q : Nat)
  | decode (syndrome : Nat)
  | frameUpdate (q : Nat)
  | postselect (predicate : Nat)
  | resetClean (q : Nat)
deriving DecidableEq, Repr

inductive StepOK (π : Policy) : RCtx -> Prim -> RCtx -> Prop where
  | direct
      (hcap : supportsGate code gate = true)
      (hcert : certAllowed π (gateCert code gate) = true) :
      StepOK π ρ (Prim.direct code gate q) ρ
  | switch
      (hexists : switchExists source target = true)
      (hcert : certAllowed π (switchCert source target) = true) :
      StepOK π ρ (Prim.switch source target q) ρ
  | produce
      (hfree : ρ r = false) :
      StepOK π ρ (Prim.produce r kind) (put ρ r)
  | consume
      (havail : ρ r = true) :
      StepOK π ρ (Prim.consume r kind gate q) (take ρ r)
  | measureL :
      StepOK π ρ (Prim.measureL targetBit q) ρ
  | decode :
      StepOK π ρ (Prim.decode syndrome) ρ
  | frameUpdate :
      StepOK π ρ (Prim.frameUpdate q) ρ
  | postselect :
      StepOK π ρ (Prim.postselect predicate) ρ
  | resetClean :
      StepOK π ρ (Prim.resetClean q) ρ

theorem unsupported_direct_rejected
    {π : Policy} {ρ Δ : RCtx} {code : Code} {gate : Gate} {q : Nat}
    (hunsupported : supportsGate code gate = false) :
    ¬ StepOK π ρ (Prim.direct code gate q) Δ := by
  intro h
  cases h with
  | direct hcap _ =>
      rw [hunsupported] at hcap
      cases hcap

theorem strict_rejects_assumed_surface_to_tetra
    {ρ Δ : RCtx} {q : Nat} :
    ¬ StepOK Policy.strict ρ
        (Prim.switch Code.surfaceD5 Code.tetra15 q) Δ := by
  intro h
  cases h with
  | switch _ hcert =>
      simp [Policy.strict, certAllowed, switchCert] at hcert

theorem no_double_consume_same_resource
    {π : Policy} {ρ Δ : RCtx} {r : Nat}
    {k k2 : ResKind} {g g2 : Gate} {q q2 : Nat}
    (hfirst : StepOK π ρ (Prim.consume r k g q) Δ) :
    ¬ StepOK π Δ (Prim.consume r k2 g2 q2) (take Δ r) := by
  intro hsecond
  cases hfirst with
  | consume _ =>
      cases hsecond with
      | consume havail2 =>
          simp [take] at havail2

inductive Prog where
  | atom (p : Prim) (e : Effect)
  | seq (p q : Prog)
  | branch (p q : Prog)
deriving Repr

def primCertAllowed (π : Policy) : Prim -> Bool
  | Prim.direct code gate _ => certAllowed π (gateCert code gate)
  | Prim.switch source target _ => certAllowed π (switchCert source target)
  | _ => true

def primConsumes (r : Nat) : Prim -> Bool
  | Prim.consume r' _ _ _ => r = r'
  | _ => false

def primProduces (r : Nat) : Prim -> Bool
  | Prim.produce r' _ => r = r'
  | _ => false

def primHasAvailableResource (ρ : RCtx) : Prim -> Bool
  | Prim.consume r _ _ _ => ρ r
  | Prim.produce r _ => !(ρ r)
  | _ => true

def Prim.stepResources (ρ : RCtx) : Prim -> RCtx
  | Prim.produce r _ => put ρ r
  | Prim.consume r _ _ _ => take ρ r
  | _ => ρ

namespace Prog

def allCertsAllowed (π : Policy) : Prog -> Bool
  | atom p _ => primCertAllowed π p
  | seq p q => allCertsAllowed π p && allCertsAllowed π q
  | branch p q => allCertsAllowed π p && allCertsAllowed π q

def linearResources (ρ : RCtx) : Prog -> Bool
  | atom p _ => primHasAvailableResource ρ p
  | seq p q =>
      linearResources ρ p && linearResources (evalResources ρ p) q
  | branch p q =>
      linearResources ρ p && linearResources ρ q

where
  evalResources (ρ : RCtx) : Prog -> RCtx
    | atom p _ => Prim.stepResources ρ p
    | seq p q => evalResources (evalResources ρ p) q
    | branch _ _ => ρ

end Prog

inductive Typed (π : Policy) : RCtx -> Prog -> RCtx -> Effect -> Prop where
  | atom
      (hstep : StepOK π ρ p ρ') :
      Typed π ρ (Prog.atom p e) ρ' e
  | seq
      (hp : Typed π ρ p ρ1 e1)
      (hq : Typed π ρ1 q ρ2 e2) :
      Typed π ρ (Prog.seq p q) ρ2 (Effect.seq e1 e2)
  | branch
      (hp : Typed π ρ p ρ' e1)
      (hq : Typed π ρ q ρ' e2) :
      Typed π ρ (Prog.branch p q) ρ' (Effect.branch e1 e2)

theorem typed_atom_cert_allowed
    {π : Policy} {ρ ρ' : RCtx} {p : Prim} {e : Effect}
    (h : Typed π ρ (Prog.atom p e) ρ' e) :
    primCertAllowed π p = true := by
  cases h with
  | atom hstep =>
      cases hstep with
      | direct _ hcert => exact hcert
      | switch _ hcert => exact hcert
      | produce _ => rfl
      | consume _ => rfl
      | measureL => rfl
      | decode => rfl
      | frameUpdate => rfl
      | postselect => rfl
      | resetClean => rfl

theorem typed_all_certs_allowed
    {π : Policy} {ρ ρ' : RCtx} {p : Prog} {e : Effect}
    (h : Typed π ρ p ρ' e) :
    Prog.allCertsAllowed π p = true := by
  induction h with
  | atom hstep =>
      cases hstep with
      | direct _ hcert => exact hcert
      | switch _ hcert => exact hcert
      | produce _ => rfl
      | consume _ => rfl
      | measureL => rfl
      | decode => rfl
      | frameUpdate => rfl
      | postselect => rfl
      | resetClean => rfl
  | seq _ _ ihp ihq =>
      simp [Prog.allCertsAllowed, ihp, ihq]
  | branch _ _ ihp ihq =>
      simp [Prog.allCertsAllowed, ihp, ihq]

def produceTEffect : Effect :=
  { err := 80, fail := 300, space := 40, time := 21, factories := 1, switches := 0 }

def consumeTEffect : Effect :=
  { err := 20, fail := 0, space := 30, time := 4, factories := 0, switches := 0 }

def injectTPlan : Prog :=
  Prog.seq
    (Prog.atom (Prim.produce 0 ResKind.tState) produceTEffect)
    (Prog.atom (Prim.consume 0 ResKind.tState Gate.T 1) consumeTEffect)

theorem injectTPlan_typed_strict :
    ∃ ρ' e, Typed Policy.strict emptyResources injectTPlan ρ' e := by
  exists take (put emptyResources 0) 0
  exists Effect.seq produceTEffect consumeTEffect
  unfold injectTPlan
  apply Typed.seq
  · apply Typed.atom
    apply StepOK.produce
    rfl
  · apply Typed.atom
    apply StepOK.consume
    simp [emptyResources, put]

theorem injectTPlan_factory_bound :
    Effect.Le produceTEffect (Effect.seq produceTEffect consumeTEffect) :=
  Effect.seq_left_bound produceTEffect consumeTEffect

theorem injectTPlan_consume_bound :
    Effect.Le consumeTEffect (Effect.seq produceTEffect consumeTEffect) :=
  Effect.seq_right_bound produceTEffect consumeTEffect

theorem bad_double_consume_second_step_rejected :
    ¬ StepOK Policy.strict
        (take (put emptyResources 0) 0)
        (Prim.consume 0 ResKind.tState Gate.T 2)
        (take (take (put emptyResources 0) 0) 0) := by
  intro h
  cases h with
  | consume havail =>
      simp [take] at havail

theorem direct_cnot_on_surface_rejected {ρ Δ : RCtx} {q : Nat} :
    ¬ StepOK Policy.strict ρ (Prim.direct Code.surfaceD5 Gate.CNOT q) Δ :=
  unsupported_direct_rejected (by rfl)

def badDoubleConsumePlan : Prog :=
  Prog.seq
    (Prog.atom (Prim.consume 0 ResKind.tState Gate.T 1) consumeTEffect)
    (Prog.atom (Prim.consume 0 ResKind.tState Gate.T 2) consumeTEffect)

theorem injectTPlan_all_certs_allowed :
    Prog.allCertsAllowed Policy.strict injectTPlan = true := by
  simp [injectTPlan, Prog.allCertsAllowed, primCertAllowed]

theorem injectTPlan_linear_resources :
    Prog.linearResources emptyResources injectTPlan = true := by
  simp [
    injectTPlan,
    Prog.linearResources,
    Prog.linearResources.evalResources,
    primHasAvailableResource,
    Prim.stepResources,
    emptyResources,
    put,
    take,
  ]

theorem badDoubleConsumePlan_not_linear_after_single_resource :
    Prog.linearResources (put emptyResources 0) badDoubleConsumePlan = false := by
  simp [
    badDoubleConsumePlan,
    Prog.linearResources,
    Prog.linearResources.evalResources,
    primHasAvailableResource,
    Prim.stepResources,
    emptyResources,
    put,
    take,
  ]

theorem typed_programs_have_allowed_certs
    {π : Policy} {ρ ρ' : RCtx} {p : Prog} {e : Effect}
    (h : Typed π ρ p ρ' e) :
    Prog.allCertsAllowed π p = true :=
  typed_all_certs_allowed h

end FTQP
