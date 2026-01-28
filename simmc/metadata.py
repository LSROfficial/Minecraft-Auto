""" 作者信息 """
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# 项目元数据
PROJECT_NAME = "SimMC-Auto"
VERSION  = (1,0,4)

# 作者元数据
Q_NUMBER = 3072252442
Q_NAME   = "帕秋莉·阿希欧姆🌙"


ATTENTIONS = [
    "不要跳脸SN和任意不是自己人的管理",
    "传播请确保群内没有管理员内鬼",
    "使用造成的任何法律责任作者不予承担"
]

console = Console()          # 单独开一条 rich 通道，不影响 loguru 文件日志

def print_banner():
    # 1. 标题渐变
    title = Text(f"{PROJECT_NAME}  v{'.'.join(map(str, VERSION))}", style="bold magenta")
    title.stylize("bold #9368E9", 0, 6)   # 帕秋莉紫 #9368E9
    console.print(title, justify="center")

    # 2. 作者信息
    console.print(
        f"[#9368E9]作者：{Q_NAME}  (QQ：{Q_NUMBER})[/]",
        justify="center"
    )

    # 3. 警示面板
    warn_text = "\n".join(f"{i}. {line}" for i, line in enumerate(ATTENTIONS, 1))
    panel = Panel(
        warn_text,
        title="[bold yellow]⚠️  使用须知[/]",
        border_style="bright_yellow",
        expand=False,
        padding=(1, 2)
    )
    console.print(panel, height=console.size.height - 5)  # 面板占满上半屏
    console.input("[dim]按 Enter 继续...[/]")        # 阻塞确认