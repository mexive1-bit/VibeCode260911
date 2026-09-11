#함수를 정의
def add(a, b):
    return a + b

#함수를 호출
result = add(3, 5)
print("The result is:", result)

#배열형식을 연습
lst = ["사과", "바나나", "체리", "포도"]
print(len(lst))  # 배열의 길이 출력

for fruit in lst:
    print(fruit)

#리스트에 새로운 요소 추가
lst.append("망고")
print("Updated list:", lst)

lst.remove("바나나")
print("List after removing '바나나':", lst)

#Tuple은 한방에 입력과 출력을 하는 배열형태
tp = (100, 200, 300)
print(len(tp))  # Tuple의 길이 출력
print(type(tp))  # Tuple의 타입 출력
for item in tp:
    print(item) 

#함수를 정의
def times(a, b):
    return a * b, a + b

#함수를 호출
result = times(4, 5)
print("The multiplication result is:", result)
