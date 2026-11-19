import vuln_lib


def a():
    b()


def b():
    c()


def c():
    d()


def d():
    e()


def e():
    vuln_lib.risky()
