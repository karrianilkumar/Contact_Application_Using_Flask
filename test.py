import smtplib

email = "karrianilkumar101@gmail.com"
password = "hcjqxeehyoljfibg"

server = smtplib.SMTP("smtp.gmail.com", 587)
server.starttls()
server.login(email, password)

print("✅ Login Successful")
server.quit()