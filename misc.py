## misc helper functions


# Adds 1 to quadkey value
def QuadKeyIncrement(qk):
    level = len(qk)
    qka = []
    qka = list(qk)
    iter = 0
    while iter < level:
        qka[iter] = int(qka[iter])
        iter = iter+1
    index = level-1
    carry = 0
    value = int(qka[index])+1
    while value > 3:
        carry = carry+1
        value = value-4
    qka[index] = value
    carrying = False
    if carry > 0:
        carrying = True
    while carrying:
        if carry > 0:
            index = index-1
            qka[index] = qka[index]+carry
            carry = 0
            value = qka[index]
            while value > 3:
                carry = carry+1
                value = value-4
            qka[index] = value
            if carry == 0:
                carrying = False
    return "".join(str(x) for x in qka)

# Find all substrings from a string
# https://stackoverflow.com/questions/4664850/how-to-find-all-occurrences-of-a-substring
def find_all(a_str, sub):
    start = 0
    while True:
        start = a_str.find(sub, start)
        if start == -1:
            return
        yield start
        start += len(sub)  # use start += 1 to find overlapping matches