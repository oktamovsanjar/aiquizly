STRUCTURE_PROMPT = """Quyidagi savollarni JSON formatga o'tkaz.
Har bir savol uchun quyidagi maydonlarni to'ldir:
- question: savol matni (string)
- options: variantlar ro'yxati (array of strings, min 2)
- correct_index: to'g'ri variant indeksi (0 dan boshlanadi, integer)
- explanation: qisqa tushuntirish (string, bo'sh bo'lishi mumkin)

Faqat JSON array qaytaril. Boshqa hech narsa yozma.

Savollar:
{questions_text}"""
