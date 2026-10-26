"""Labels for the existing V3/V4 solution taxonomy, not a second PL topic tree."""
TYPE_CATALOG={
 'methods':{
  'kinematic_equations':'运动学方程','free_body_diagram':'受力分析','newton_second_law':'牛顿第二定律列式',
  'work_energy':'功与能','momentum_conservation':'动量守恒','rotational_dynamics':'转动动力学',
  'simple_harmonic_motion':'简谐运动','central_force':'中心力','inertia_integral':'转动惯量积分',
  'vector_components':'矢量分解与合成','calculus_kinematics':'微积分运动学','graph_slope_area':'图像斜率与面积','relative_velocity':'相对速度','projectile_motion':'抛体运动'},
 'structures':{
  'particle_motion':'质点运动','force_balance':'力的平衡','force_acceleration':'合力与加速度',
  'energy_transfer':'能量转化','collision':'碰撞','rigid_body_rotation':'刚体转动',
  'oscillator':'振动模型','orbital_motion':'轨道运动','mass_distribution':'质量分布',
  'vector_system':'矢量系统','motion_graph':'运动图像','reference_frame':'参考系','projectile':'抛体'}}

def validate_types(methods,structures):
 result={}
 for field,values in [('methods',methods),('structures',structures)]:
  if not isinstance(values,list) or len(values)>12 or any(not isinstance(v,str) or v not in TYPE_CATALOG[field] for v in values):
   raise ValueError('请选择已有解题类型；无法确认时可留空')
  result[field]=list(dict.fromkeys(values))
 return result
