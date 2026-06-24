"""
DailyBot 统一入口
用法:
    python run.py              # 执行一次日报生成
    python run.py --scheduler  # 注册定时任务并退出
    python run.py --status     # 查看调度器状态
"""
import os
import sys

# 确保在项目根目录运行
os.chdir(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    args = sys.argv[1:]

    if not args:
        # 默认：执行一次日报生成
        from dailybot_scheduler import execute_trigger, setup_logging
        log = setup_logging()
        execute_trigger(log)
    elif "--scheduler" in args:
        os.execvp(sys.executable, [sys.executable, "dailybot_scheduler.py"])
    elif "--status" in args:
        os.execvp(sys.executable, [sys.executable, "dailybot_scheduler.py", "--status"])
    else:
        print(f"未知参数: {args}")
        print("用法: python run.py [--scheduler|--status]")
