import numpy as np
import matplotlib.pyplot as plt

# 生成一个基于黄金比例的五重对称魔法阵
phi = (1 + np.sqrt(5)) / 2
angles = np.linspace(0, 2*np.pi, 6)[:-1]
r = 1.0
x = r * np.cos(angles)
y = r * np.sin(angles)

# 绘制星芒与内嵌正十二面体投影
plt.figure(figsize=(6,6))
for i in range(5):
    for j in range(i+1, 5):
        plt.plot([x[i], x[j]], [y[i], y[j]], 'purple', alpha=0.7)

# 中心符文：水之印
plt.text(0, 0, "💧", fontsize=40, ha='center', va='center')
plt.axis('equal')
plt.axis('off')
plt.title("Dodecahedral Water Sigil - by 张君羽")
plt.show()