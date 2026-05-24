STRUCTURE_PROMPT = """Quyidagi matndan test savollarini topib, JSON formatga o'tkaz.

1. SAVOL ANIQLASH
Quyidagi har qanday formatda yozilgan savollarni top:
- Raqamli: "1.", "1)", "№1", "1-savol"
- So'roq belgili: "...?" bilan tugagan gap
- Kalit so'zli: "Savol:", "Q:", "Вопрос:", "Question:" dan keyin kelgan gap
- Jadval: birinchi ustun savol, qolgan ustunlar variant bo'lishi mumkin
Sarlavha, tushuntirish, umumiy matn — savol emas, o'tkazib yubor.

2. VARIANT ANIQLASH
Faqat matnda MAVJUD variantlarni ol. O'zing variant TO'QIMA.
Variantlar quyidagi istalgan belgidan keyin kelishi mumkin:
A) B) C) D), а) б) в) г), a. b. c. d., 1) 2) 3) 4), +/-, *, •, –, jadval ustunlari
Variantning belgisini (A), •) options ga kiritma — faqat matn qismini yoz.
Agar savolda variant yo'q bo'lsa — o'sha savolni o'tkazib yubor.

3. TO'G'RI JAVOB ANIQLASH
AVVAL matnda javob belgisi qidirilsin:
- "Javob: B", "Answer: C", "Правильный ответ: 2" kabi yozuvlar
- Variantning oldida + yoki * belgisi: "+B)", "*C."
- Variant qalin/kursiv: **B**, _C_
- Variant oxirida ✓ yoki (to'g'ri) yozuvi
Bunday belgi topilsa — O'SHA variantning indeksini correct_index qilib qo'y. O'zing taxmin QILMA.

Agar hech qanday belgi yo'q bo'lsa — bilimingga asoslanib to'g'ri javobni o'zing aniqlaysan va correct_index qo'yasan.

Har bir savol uchun:
- question: savol matni (string)
- options: variantlar ro'yxati (array of strings, min 2, max 6)
- correct_index: to'g'ri variant indeksi, 0 dan boshlanadi (integer, hech qachon null bo'lmasin)
- explanation: matnda tushuntirish berilgan bo'lsa yoz, aks holda bo'sh string

MUHIM: Har bir savolni FAQAT BIR MARTA qaytaR. Bir xil yoki juda o'xshash savol matnda ikki marta uchrasa — faqat bittasini ol, ikkinchisini o'tkazib yubor.

Faqat JSON qaytaril: {{"questions": [...]}}
Boshqa hech narsa yozma.

Matn:
{questions_text}"""
