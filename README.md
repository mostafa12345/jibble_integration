# 🚀 Jibble Integration for Frappe ERPNext

A seamless integration between **[Jibble](https://www.jibble.io/)** and **Frappe ERPNext** that automatically logs **Attendance**, **Check-In**, and **Check-Out** with **location tracking** based on shift settings.

---

## 📌 Features

✅ Auto-creates `Employee Checkin` and `Employee Checkout` records  
✅ Uses employee email for precise user matching  
✅ Fallback to full name if email not found (e.g. for users like *Mahmoud*)  
✅ Includes location data from Jibble  
✅ Runs automatically every 10 minutes via Frappe Scheduler  
✅ Fully customizable and open-source  

---

## 🛠️ ERPNext Configuration

### 1. Enable Auto Attendance in Shift

1. Navigate to **HR > Shift Type**
2. Open your shift (e.g., `9 - 5`)
3. Enable ✅ **"Enable Auto Attendance"**
4. Assign this shift to employees using **Shift Assignment**

### 2. Configure Employee Doctype to Use Email

1. Go to **DocType > Employee**
2. Under **View Settings**:
   - Set **Title Field** = `user_id`
   - Add `user_id` to **Search Fields**
3. This allows mapping check-ins using the employee’s email from Jibble

🖼️ *Example:*  
![Shift Type Screenshot](https://amunet.pharaonx.com/files/b7b16e2e-0e3b-451a-9fb6-6b1d660ae2c1.png)  
![Employee DocType Screenshot](https://amunet.pharaonx.com/files/57844203-50a6-42dd-b5a6-d6c1d877136b.png)

---

## ⚙️ Installation Instructions

### 📥 1. Clone the App

```bash
cd ~/frappe-bench/apps
git clone https://github.com/mostafa12345/jibble_integration.git
