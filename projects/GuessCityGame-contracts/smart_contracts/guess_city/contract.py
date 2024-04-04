import beaker
import pyteal as pt
from pyteal import *
import random

app = beaker.Application("guess_city")
class GuessState:
    guessing_city = beaker.GlobalStateValue(
        stack_type=pt.TealType.bytes, default=pt.Bytes("")
    )
    city = beaker.LocalStateValue(stack_type=pt.TealType.bytes, default=pt.Bytes(""))

    player_one = beaker.GlobalStateValue(
        stack_type=pt.TealType.bytes,
        descr=" Account of the first player",
        default=pt.Bytes("No player one"),
    )
    player_two = beaker.GlobalStateValue(
        stack_type=pt.TealType.bytes,
        descr="Account of the second player",
        default=pt.Bytes("No player two"),
    )
    wager = beaker.GlobalStateValue(
        stack_type=pt.TealType.uint64,
        descr="Betting amount",
        default=pt.Int(0),
    )
    result = beaker.GlobalStateValue(
        stack_type=pt.TealType.bytes,
        descr="",
        default=pt.Bytes(""),
    )

app = beaker.Application("guess_city", state=GuessState)

@app.create(bare=True)
def create() -> pt.Expr:
    return app.initialize_global_state()

@app.opt_in(bare=True)
def opt_in() -> pt.Expr:
    return pt.Seq(
        pt.If(app.state.player_one.get() == pt.Bytes("No player one"))
        .Then(app.state.player_one.set(pt.Txn.sender()))
        .ElseIf(app.state.player_two.get() == pt.Bytes("No player two"))
        .Then(app.state.player_two.set(pt.Txn.sender()))
        .Else(pt.Reject()),
        app.initialize_local_state(addr=pt.Txn.sender()),
    )


@app.external
def play(
    city: pt.abi.String, payment: pt.abi.PaymentTransaction, *, output: pt.abi.Uint64
) -> pt.Expr:
    pt.Assert(
        pt.And(
            payment.get().receiver() == pt.Global.current_application_address(),
            app.state.city[pt.Txn.sender()].get() == pt.Bytes(""),
        ),
    )

    return pt.Seq(
        If(app.state.guessing_city.get() == app.state.guessing_city.default).Then(
            app.state.guessing_city.set(transform_word(pt.Int(random.randint(0, 7)))),
        ),
        app.state.wager.set(payment.get().amount()),
        app.state.city.set(city.get()),
    )


@pt.Subroutine(pt.TealType.bytes)
def transform_word(rndNum: pt.Expr) -> pt.Expr:
    return pt.Return(
        pt.Cond(
            [rndNum == pt.Int(0), pt.Bytes("Belgrade")],
            [rndNum == pt.Int(1), pt.Bytes("Wien")],
            [rndNum == pt.Int(2), pt.Bytes("Athens")],
            [rndNum == pt.Int(3), pt.Bytes("London")],
            [rndNum == pt.Int(4), pt.Bytes("Paris")],
            [rndNum == pt.Int(5), pt.Bytes("Madrid")],
            [rndNum == pt.Int(6), pt.Bytes("Bern")],
            [rndNum == pt.Int(7), pt.Bytes("Budapest")],
        )
    )


@app.external
def game_result(opponent: pt.abi.Account, *, output: pt.abi.String) -> pt.Expr:
    guess1 = pt.ScratchVar(pt.TealType.bytes)
    guess2 = pt.ScratchVar(pt.TealType.bytes)
    wager = pt.ScratchVar(pt.TealType.uint64)
    p1 = pt.abi.String()
    return pt.Seq(
        guess1.store(app.state.city[pt.Txn.sender()].get()),
        guess2.store(app.state.city[pt.Txn.accounts[1]].get()),
        wager.store(app.state.wager.get()),
        pt.If(guess1.load() == app.state.guessing_city.get())
        .Then(
            pt.Seq(
                pay(pt.Int(0), wager.load()),
                app.state.result.set(pt.Bytes("Pobedili ste")),
                p1.set(app.state.result.get()),
                output.set(p1),
            )
        )
        .ElseIf(guess2.load() == app.state.guessing_city.get())
        .Then(
            pt.Seq(
                pay(pt.Int(1), wager.load()),
                app.state.result.set(pt.Bytes("Izgubili ste")),
                p1.set(app.state.result.get()),
                output.set(p1),
            )
        )
        .ElseIf(
            pt.And(
                guess1.load() == app.state.guessing_city.get(),
                guess2.load() == app.state.guessing_city.get(),
            )
        )
        .Then(
            pt.Seq(
                pay(
                    pt.Int(0),
                    wager.load(),
                ),
                pay(
                    pt.Int(1),
                    wager.load(),
                ),
                app.state.result.set(pt.Bytes("Draw result")),
                p1.set(app.state.result.get()),
                output.set(p1),
            )
        ),
    )


@pt.Subroutine(pt.TealType.none)
def pay(acc_index: pt.Expr, amount: pt.Expr) -> pt.Expr:
    return pt.Seq(
        pt.InnerTxnBuilder.Begin(),
        pt.InnerTxnBuilder.SetFields(
            {
                pt.TxnField.type_enum: pt.TxnType.Payment,
                pt.TxnField.receiver: pt.Txn.accounts[acc_index],
                pt.TxnField.amount: amount,
            }
        ),
        pt.InnerTxnBuilder.Submit(),
    )


@app.external
def sum_of_fees(*, output: pt.abi.Uint64) -> pt.Expr:
    totalFees = ScratchVar(TealType.uint64)
    i = ScratchVar(TealType.uint64)
    return Seq(
        i.store(Int(0)),
        totalFees.store(Int(0)),
        While(i.load() < Global.group_size()).Do(
            totalFees.store(totalFees.load() + Gtxn[i.load()].fee()),
            i.store(i.load() + Int(1)),
        ),
        output.set(totalFees.load()),
    )


@app.external
def word_length(*, output: pt.abi.Tuple2[pt.abi.String, pt.abi.Uint64]) -> pt.Expr:
    counter = pt.abi.Uint64()
    word = pt.abi.String()
    return pt.Seq(
        counter.set(Len(app.state.guessing_city.get())),
        word.set(Bytes("Number of letters: ")),
        output.set(word, counter),
    )
