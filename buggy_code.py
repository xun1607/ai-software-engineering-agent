def calculate_average(numbers):
    total = sum(numbers)
    # Lỗi tiềm ẩn: Nếu mảng rỗng sẽ bị ZeroDivisionError
    avg = total / len(numbers)
    return avg

print(calculate_average([]))
