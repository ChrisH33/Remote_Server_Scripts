from datetime import datetime
now = datetime.now()
suffix = "th" if 11 <= now.day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(now.day % 10, "th")
time = f"{now.strftime('%H:%M')}, {now.day}{suffix} {now.strftime('%b')}"
print(time)