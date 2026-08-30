import asyncio
from kolobot.local_ocr import UnlimitedOCRService

async def main():
    ocr = UnlimitedOCRService.get_instance()
    print("Extracting text...")
    text = await ocr.extract_text(r"downloads\tmp\b791aad224a04758b4c3ec01533e9c50.jpg", "image/jpeg")
    print("Result:")
    print(text)

if __name__ == "__main__":
    asyncio.run(main())
