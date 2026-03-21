import { api } from "./client";

export const getProviders = () => api("/config/providers");
