import random
questions = [
    {'question': 'What is the value of x in the equation 2x + 5 = 11?', 'options': ['2', '3', '4', '5'], 'answer': '3'},
    {'question': 'What is the derivative of the function f(x) = x^2?', 'options': ['2x', 'x^2', '2', 'x'], 'answer': '2x'},
    {'question': 'What is the value of the integral of the function f(x) = x^2 from 0 to 1?', 'options': ['1/3', '1/2', '2/3', '3/4'], 'answer': '1/3'},
    {'question': 'What is the formula for the area of a circle?', 'options': ['A = πr^2', 'A = 2πr', 'A = πr', 'A = r^2'], 'answer': 'A = πr^2'},
    {'question': 'What is the value of the constant e?', 'options': ['2.71', '3.14', '1.61', '0.58'], 'answer': '2.71'},
    {'question': 'What is the distance between two points (x1, y1) and (x2, y2) in a coordinate plane?', 'options': ['√((x2 - x1)^2 + (y2 - y1)^2)', '√((x2 - x1)^2 - (y2 - y1)^2)', '√((x2 - x1)^2 + (y2 - y1)^2)/2', '√((x2 - x1)^2 - (y2 - y1)^2)/2'], 'answer': '√((x2 - x1)^2 + (y2 - y1)^2)'},
    {'question': 'What is the equation of a line that passes through the points (x1, y1) and (x2, y2)?', 'options': ['y - y1 = (y2 - y1)/(x2 - x1)(x - x1)', 'y - y1 = (y2 - y1)/(x2 - x1)(x - x2)', 'y - y1 = (y2 - y1)/(x2 - x1)(x + x1)', 'y - y1 = (y2 - y1)/(x2 - x1)(x + x2)' ], 'answer': 'y - y1 = (y2 - y1)/(x2 - x1)(x - x1)'},
    {'question': 'What is the formula for the volume of a sphere?', 'options': ['V = (4/3)πr^3', 'V = (4/3)πr^2', 'V = (4/3)πr', 'V = (4/3)π/r'], 'answer': 'V = (4/3)πr^3'},
    {'question': 'What is the value of the expression (2^3 + 3^2)/(4^2 - 2^2)?', 'options': ['2', '3', '4', '5'], 'answer': '2'},
    {'question': 'What is the equation of the circle with center (h, k) and radius r?', 'options': ['(x - h)^2 + (y - k)^2 = r^2', '(x - h)^2 - (y - k)^2 = r^2', '(x - h)^2 + (y - k)^2 = -r^2', '(x - h)^2 - (y - k)^2 = -r^2'], 'answer': '(x - h)^2 + (y - k)^2 = r^2'},
    {'question': 'What is the formula for the surface area of a cube?', 'options': ['A = 6s^2', 'A = 6s', 'A = s^2', 'A = s'], 'answer': 'A = 6s^2'},
    {'question': 'What is the value of the expression sin(30°) + cos(60°)?', 'options': ['1', '2', '3', '4'], 'answer': '1'},
    {'question': 'What is the equation of the line that passes through the point (x1, y1) and has a slope of m?', 'options': ['y - y1 = m(x - x1)', 'y - y1 = -m(x - x1)', 'y - y1 = m(x + x1)', 'y - y1 = -m(x + x1)' ], 'answer': 'y - y1 = m(x - x1)'},
]
for question in questions:
    print('Question: ' + question['question'])
    print('Options: ' + ', '.join(question['options']))
    print('Answer: ' + question['answer'])
    print('')