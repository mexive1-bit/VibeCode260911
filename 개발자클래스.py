#라이브러리를 사용
import glob

#raw string notation(날것 그대로 사용)
print(glob.glob(r"C:\work\*.py"))

#Developer클래스를 정의하면서
#id, name, skill이라는 변수가 있고,
#printInfo()메서드가 해당 정보를 출력함.
class Developer:
    def __init__(self, id, name, skill):
        self.id = id
        self.name = name
        self.skill = skill

    def printInfo(self):
        print("ID: {0}, Name: {1}, Skill: {2}".format(self.id, self.name, self.skill))

#인스턴스를 생성
dev1 = Developer(1, "Alice", "Python")
dev2 = Developer(2, "Bob", "JavaScript")

#정보 출력
dev1.printInfo()
dev2.printInfo()