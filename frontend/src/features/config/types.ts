export interface DurationOption {
  minutes: number;
  label: string;
  question_count: number;
}

export interface InterviewPublicConfig {
  jd_min_chars: number;
  jd_max_chars: number;
  default_duration_minutes: number;
  duration_min_minutes: number;
  duration_max_minutes: number;
  role_requirements_max_items: number;
  role_requirement_max_chars: number;
  role_skills_max_items: number;
  role_skill_max_chars: number;
  duration_options: DurationOption[];
}

export interface PublicConfig {
  app_name: string;
  interview: InterviewPublicConfig;
}

/** Matches settings/config.yaml so the UI still works if the endpoint is down. */
export const PUBLIC_CONFIG_FALLBACK: PublicConfig = {
  app_name: "AI Mock Interview Platform",
  interview: {
    jd_min_chars: 200,
    jd_max_chars: 20000,
    default_duration_minutes: 30,
    duration_min_minutes: 15,
    duration_max_minutes: 90,
    role_requirements_max_items: 20,
    role_requirement_max_chars: 300,
    role_skills_max_items: 30,
    role_skill_max_chars: 100,
    duration_options: [
      { minutes: 15, label: "15 min", question_count: 5 },
      { minutes: 30, label: "30 min", question_count: 7 },
      { minutes: 45, label: "45 min", question_count: 8 },
      { minutes: 60, label: "60 min", question_count: 9 },
    ],
  },
};
