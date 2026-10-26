/* Interface direction only. Keep the three existing representative topics. */
window.PathlineReviewContract={
  version:1,
  flow:['recall','explain_or_apply','repair','recheck'],
  blueprint_fields:['core_targets','recall_prompts','application_prompts','common_errors','hint_ladder','repair_sources'],
  representative_topics:['2.5','5.4','7.5'],
  evidence_types:['exposure','practice','learning_repair','assessment'],
  goals_en:{
    '2.5':['Explain acceleration using net force and mass: ΣF = ma.','Choose a system, draw a free-body diagram and resolve Newton’s second law along axes.','Distinguish forces on one object from action–reaction forces on different objects.'],
    '5.4':['Explain rotational inertia in terms of mass distribution about an axis.','Use I = Σmr², I = ∫r²dm and the parallel-axis theorem.','Distinguish changes in mass distribution from changes in the rotation axis.'],
    '7.5':['Explain how a small-angle pendulum’s period depends on length and gravity.','Describe a physical pendulum using rotational inertia and the pivot-to-centre-of-mass distance.','Identify the conditions under which the period formulas apply.']
  }
};
