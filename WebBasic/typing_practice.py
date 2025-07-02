from typing import TYPE_CHECKING

# 此变量在类型检查时为 True，而在运行时为 False
if TYPE_CHECKING:
    # 此处的代码只有在类型检查时才会被使用，在运行时不会执行
    # 因此即使实际Python环境中并没有安装 vllm package，运行时此处的导入也不会报错
    from vllm import LLM


# 函数参数里类型，必须要使用 '' 括起来，实现前向引用 ------------ KEY
def f1(llm: 'LLM') -> str:
    # 函数内部的类型参数，因为是局部变量，不需要使用 ''
    vllm: LLM = 'SOME4'
    print(vllm)
    return llm


def f2() -> str:
    # 这里作为局部变量，也不需要使用 ''
    vllm: LLM = 'SOME5'
    print(vllm)
    return vllm


if __name__ == '__main__':
    # 全局的类型参数所有地方都需要使用 ''
    # vllm1: LLM = 'SOME1'
    vllm1: 'LLM' = 'SOME1'
    print(vllm1)

    # 即使第二次使用类型参数也需要使用 ''
    # vllm2: LLM = 'SOME2'
    vllm2: 'LLM' = 'SOME2'
    print(vllm2)

    print(f1('SOME3'))

    f2()
