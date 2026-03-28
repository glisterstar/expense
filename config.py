import os
from dotenv import load_dotenv

load_dotenv()

# LINE Bot
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")

# Google
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")

# Sheet names
SHEET_EXPENSES = "รายการ"
SHEET_MONTHLY = "สรุปรายเดือน"

# Category keywords mapping
CATEGORY_KEYWORDS = {
    "อาหาร": [
        "ข้าว", "กับข้าว", "อาหาร", "ส้มตำ", "ก๋วยเตี๋ยว", "ผัด", "แกง",
        "ต้ม", "ย่าง", "ทอด", "food", "meal", "rice", "noodle",
        "ไก่", "หมู", "ปลา", "กุ้ง", "เนื้อ", "ผัก", "ไข่",
    ],
    "เครื่องดื่ม": [
        "น้ำ", "กาแฟ", "ชา", "นม", "น้ำอัดลม", "เบียร์", "เหล้า",
        "coffee", "tea", "water", "drink", "juice", "โค้ก", "เป๊ปซี่",
        "สตาร์บัคส์", "starbucks", "cafe", "คาเฟ่",
    ],
    "ของใช้": [
        "สบู่", "แชมพู", "ผงซักฟอก", "กระดาษ", "ทิชชู่", "แปรงสีฟัน",
        "ยาสีฟัน", "ถุงขยะ", "น้ำยา", "ผ้าอ้อม", "household",
    ],
    "เดินทาง": [
        "น้ำมัน", "แก๊ส", "ค่ารถ", "grab", "bolt", "taxi", "แท็กซี่",
        "bts", "mrt", "ทางด่วน", "ที่จอดรถ", "ค่าทาง", "เติมน้ำมัน",
    ],
    "สุขภาพ": [
        "ยา", "หมอ", "โรงพยาบาล", "คลินิก", "วิตามิน", "pharmacy",
        "แมส", "หน้ากาก", "เจล", "แอลกอฮอล์",
    ],
    "ช้อปปิ้ง": [
        "เสื้อ", "กางเกง", "รองเท้า", "กระเป๋า", "เครื่องสำอาง",
        "ครีม", "fashion", "clothing", "shoes",
    ],
    "อื่นๆ": [],
}

# Channel detection keywords
CHANNEL_KEYWORDS = {
    "Shopee": ["shopee", "ช้อปปี้", "shopee express", "spx"],
    "Lazada": ["lazada", "ลาซาด้า"],
    "7-Eleven": ["7-eleven", "7-11", "เซเว่น", "cp all"],
    "Lotus's": ["lotus", "โลตัส", "tesco"],
    "Big C": ["big c", "บิ๊กซี"],
    "Makro": ["makro", "แม็คโคร"],
    "Tops": ["tops", "ท็อปส์"],
    "Grab": ["grab", "แกร็บ"],
    "LINE Man": ["lineman", "line man", "ไลน์แมน"],
    "Foodpanda": ["foodpanda", "ฟู้ดแพนด้า"],
}
