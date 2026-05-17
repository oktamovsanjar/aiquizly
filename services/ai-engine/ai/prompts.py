STRUCTURE_PROMPT = """Quyidagi matndan test savollarini topib, JSON formatga o'tkaz.

Matn turli formatlarda bo'lishi mumkin: raqamlangan, jadval, erkin matn va hokazo.
Faqat haqiqiy test savollarini ajrat — umumiy matn, tushuntirish, sarlavhalarni o'tkazib yubor.

Har bir savol uchun:
- question: savol matni (string)
- options: variantlar ro'yxati (array of strings, min 2, max 6)
- correct_index: to'g'ri variant indeksi, 0 dan boshlanadi (integer)
- explanation: qisqa tushuntirish yoki bo'sh string

Faqat JSON qaytaril: {{"questions": [...]}}
Boshqa hech narsa yozma.

Matn:
{questions_text}"""
