# 범용 저장소 인터페이스 → S3(예상)
class Storage:
    def load(self, key: str):
        pass

    def save(self, key: str, value):
        pass
