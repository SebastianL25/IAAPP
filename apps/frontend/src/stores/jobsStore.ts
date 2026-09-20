import { create } from "zustand";

import type { JobProgressMessage } from "../types/api";

interface JobsState {
  jobsById: Record<string, JobProgressMessage>;
  setJob: (msg: JobProgressMessage) => void;
}

export const useJobsStore = create<JobsState>((set) => ({
  jobsById: {},
  setJob: (msg) =>
    set((state) => ({
      jobsById: { ...state.jobsById, [msg.job_id]: msg },
    })),
}));
