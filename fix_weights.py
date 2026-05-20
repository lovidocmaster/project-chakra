lines = open('v15_chakra.py', 'r', encoding='utf-8').readlines()

for i, line in enumerate(lines):
    if 'self.weights.boost_top(3)' in line:
        lines[i] = line.replace('self.weights.boost_top(3)', '# self.weights.boost_top(3)  # TODO')
    if 'self.weights.reduce_bottom(3)' in line:
        lines[i] = line.replace('self.weights.reduce_bottom(3)', '# self.weights.reduce_bottom(3)  # TODO')

open('v15_chakra.py', 'w', encoding='utf-8').writelines(lines)
print('Fixed AgentWeights error')
