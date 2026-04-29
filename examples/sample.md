设系统中共有 K 个用户，每个用户需要完成一次 edge inference task。

由 $x_i$ 可得第 k 个用户的 transmission delay 为 $t_k = D_k/r_k$。若信道带宽为 $B$，则速率可以写作 $r_k = B\log_2(1+\gamma_k)$。

$$
\begin{aligned}
\min_{\mathbf{x}, \mathbf{p}} \quad & \sum_{k=1}^{K} t_k \\
\text{s.t.} \quad & \sum_{k=1}^{K} p_k \leq P_{\max} \\
& x_k \in \{0,1\}, \quad k=1,\ldots,K
\end{aligned}
$$

因此，优化目标可以理解为在资源约束下最小化所有用户的总时延。
