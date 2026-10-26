(function(root){
  'use strict';
  const pair=(zh,en)=>({zh,en});
  const numeric=(id,zh,en,value)=>({id,text:pair(zh,en),kind:'number',value});
  const blueprints={
    '2.5':{
      core_targets:['net-force','acceleration','same-body'],
      recall_prompts:[{id:'newton-recall',kind:'recall',text:pair('不看教材，写出牛顿第二定律，并说明式中的力指什么。','Without notes, write Newton’s second law and explain which force it uses.'),required:[['合力|净力|净外力|net\\s*(external\\s*)?force|sum.*force|所有.*力|总.*力'],['f\\s*=\\s*m\\s*[*·]?\\s*a|ma\\s*=|a\\s*=\\s*f\\s*\\/\\s*m','加速度.*质量|质量.*加速度|acceleration.*mass|mass.*acceleration']],reject:['(?:不是|并非|非)\\s*(?:合力|净力|净外力)|(?:not|isn’t|isn\\x27t)\\s+(?:the\\s+)?net\\s+force']}],
      application_prompts:[numeric('newton-apply','一个 2 kg 箱子受到向右 10 N、向左 4 N 的水平力。取向右为正，加速度是多少 m/s²？只填写数值。','A 2 kg box has horizontal forces of 10 N right and 4 N left. Right is positive. What is its acceleration in m/s²? Enter a number.',3),numeric('newton-check','一辆 3 kg 小车受到向右 15 N、向左 3 N 的水平力。取向右为正，加速度是多少 m/s²？','A 3 kg cart has forces of 15 N right and 3 N left. Right is positive. What is its acceleration in m/s²?',4),numeric('newton-repaired-check','一个 4 kg 物体受到向右 8 N、向左 20 N 的水平力。取向右为正，加速度是多少 m/s²？','A 4 kg object has forces of 8 N right and 20 N left. Right is positive. What is its acceleration in m/s²?',-3)],
      common_errors:[pair('把单个力当成合力。','Using one force instead of the net force.')],
      hint_ladder:[pair('先选定一个物体，想一想哪些力作用在它身上。','Choose one body and think about the forces acting on it.'),pair('沿同一个方向列出所有外力，带符号相加，再考虑质量。','List all external forces along one axis, add them with signs, then consider the mass.')],
      repair_sources:[{kind:'reading',ref:'os-reading-5.3-p203',label:'OpenStax §5.3'},{kind:'example',ref:'os-example-5.2',label:'Example 5.2'}]
    },
    '5.4':{
      core_targets:['mass-distribution','axis-distance-squared'],
      recall_prompts:[{id:'inertia-recall',kind:'recall',text:pair('不看教材，写出若干质点的转动惯量关系，并说明距离从哪里量起。','Without notes, write rotational inertia for point masses and say where the distance is measured from.'),required:[['转轴|旋转轴|axis'],['m\\s*[*·]?\\s*r\\s*(\\^2|\\*\\*2)|mr2|r.*平方|distance.*squared|square.*distance']],reject:['r.*(?:不是|not).*(?:转轴|axis)']}],
      application_prompts:[numeric('inertia-apply','一个 2 kg 质点距转轴 3 m。转动惯量是多少 kg·m²？只填写数值。','A 2 kg point mass is 3 m from the rotation axis. What is its rotational inertia in kg·m²? Enter a number.',18),numeric('inertia-check','两个各 1 kg 的质点分别距转轴 1 m 和 2 m。总转动惯量是多少 kg·m²？','Two 1 kg point masses are 1 m and 2 m from an axis. What is their total rotational inertia in kg·m²?',5),numeric('inertia-repaired-check','两个各 2 kg 的质点分别距转轴 1 m 和 3 m。总转动惯量是多少 kg·m²？','Two 2 kg point masses are 1 m and 3 m from an axis. What is their total rotational inertia in kg·m²?',20)],
      common_errors:[pair('只加质量，或把距离的一次方当成平方。','Adding only masses or using distance instead of distance squared.')],
      hint_ladder:[pair('相同质量放在不同位置，转动时的作用一样吗？','Does the same mass contribute equally at different positions?'),pair('分别考虑每个质点的质量与到转轴的垂直距离，再把贡献相加。','For each point mass, consider its mass and perpendicular distance from the axis, then add the contributions.')],
      repair_sources:[{kind:'example',ref:'os-example-10.8',label:'Example 10.8'},{kind:'figure',ref:'os-figure-10.19',label:'Figure 10.19'},{kind:'supplement',ref:'ap-inertia-integrals',label:'AP Supplement · Inertia'}]
    },
    '7.5':{
      core_targets:['small-angle','simple-period','physical-inertia'],
      recall_prompts:[{id:'pendulum-recall',kind:'recall',text:pair('不看教材，写出单摆周期公式及适用条件；再说明物理摆还需要哪个描述质量分布的量。','Without notes, write the simple pendulum period and its condition. Which quantity describing mass distribution is also needed for a physical pendulum?'),required:[['小角|small[ -]?angle'],['转动惯量|moment of inertia|rotational inertia|\\bi\\b'],['2\\s*[πp]|2pi'],['l\\s*\\/\\s*g|length.*gravit|摆长.*重力']],reject:['不是小角|不限.*小角|not.*small[ -]?angle']}],
      application_prompts:[numeric('pendulum-apply','小角振动、相同重力下，单摆摆长变为原来的 4 倍。周期变为原来的几倍？','For small oscillations at the same gravity, a simple pendulum’s length becomes 4 times as large. By what factor does the period change?',2),numeric('pendulum-check','小角振动、相同重力下，另一单摆摆长变为原来的 9 倍。周期变为原来的几倍？','For small oscillations at the same gravity, another pendulum’s length becomes 9 times as large. By what factor does its period change?',3),numeric('pendulum-repaired-check','小角振动、相同重力下，单摆摆长变为原来的 1/4。周期变为原来的几倍？填写小数。','For small oscillations at the same gravity, a pendulum’s length becomes one quarter as large. By what factor does the period change? Enter a decimal.',0.5)],
      common_errors:[pair('忘记小角条件，或把周期与摆长当成线性关系。','Missing the small-angle condition or assuming period is linear in length.')],
      hint_ladder:[pair('先回想这个周期关系适用于怎样的摆动幅度。','First recall the amplitude condition for this period relationship.'),pair('比较周期公式中摆长的位置；物理摆还要考虑转轴、重心和转动惯量。','Look at how length enters the period formula. A physical pendulum also depends on its pivot, centre of mass and rotational inertia.')],
      repair_sources:[{kind:'figure',ref:'os-figure-15.20',label:'Figure 15.20'},{kind:'example',ref:'os-example-15.3',label:'Example 15.3'},{kind:'reading',ref:'os-reading-15.4-simple-physical-p731',label:'OpenStax §15.4 · Physical pendulum'}]
    }
  };
  if(typeof module!=='undefined'&&module.exports)module.exports=blueprints;else root.MFBlueprints=blueprints;
})(typeof window==='undefined'?globalThis:window);
