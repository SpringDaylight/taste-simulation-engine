import { useEffect, useState } from "react";
import { getAccessToken } from "../api/http";
import { getCurrentUser } from "../api/A7_profile";
import { checkUserPreferenceExists, getUserPreference } from "../api/userPreferences";
import { getArrayFromStorage, getStringFromStorage } from "../utils/storage";

type TasteSurveyStorage = {
  selectedGenres: string[];
  avoidedGenres: string[];
  savedKeywords: string[];
  savedVibe: string;
  tasteContext: string;
  tasteOrigin: string;
  hasSurveyData: boolean;
};

const emptySurveyState: TasteSurveyStorage = {
  selectedGenres: [],
  avoidedGenres: [],
  savedKeywords: [],
  savedVibe: "",
  tasteContext: "",
  tasteOrigin: "",
  hasSurveyData: false,
};

export const useTasteSurveyStorage = (refreshKey?: number): TasteSurveyStorage => {
  const [state, setState] = useState<TasteSurveyStorage>(emptySurveyState);

  useEffect(() => {
    let isCancelled = false;
    const isLoggedIn = Boolean(getAccessToken());

    const setFromLocal = () => {
      const selectedGenres = getArrayFromStorage("mw_taste_genres");
      const avoidedGenres = getArrayFromStorage("mw_taste_avoid_genres");
      const savedKeywords = getArrayFromStorage("mw_taste_keywords");
      const savedVibe = getStringFromStorage("mw_taste_vibe").trim();
      const tasteContext = getStringFromStorage("mw_taste_context").trim();
      const tasteOrigin = getStringFromStorage("mw_taste_origin").trim();
      const hasSurveyData =
        selectedGenres.length > 0 ||
        avoidedGenres.length > 0 ||
        savedKeywords.length > 0 ||
        Boolean(savedVibe) ||
        Boolean(tasteContext) ||
        Boolean(tasteOrigin);

      if (!isCancelled) {
        setState({
          selectedGenres,
          avoidedGenres,
          savedKeywords,
          savedVibe,
          tasteContext,
          tasteOrigin,
          hasSurveyData,
        });
      }
    };

    const setFromServer = async () => {
      try {
        const currentUser = await getCurrentUser();
        const exists = await checkUserPreferenceExists(currentUser.id);
        if (!exists.exists) {
          if (!isCancelled) {
            setState(emptySurveyState);
          }
          return;
        }
        const preference = await getUserPreference(currentUser.id);
        const survey = preference.preference_vector_json?.taste_survey;

        const selectedGenres = survey?.genres ?? [];
        const avoidedGenres = survey?.avoid_genres ?? [];
        const savedKeywords = survey?.keywords ?? [];
        const savedVibe = survey?.vibe ?? "";
        const tasteContext = survey?.context ?? "";
        const tasteOrigin = survey?.origin ?? "";
        const hasSurveyData =
          selectedGenres.length > 0 ||
          avoidedGenres.length > 0 ||
          savedKeywords.length > 0 ||
          Boolean(savedVibe) ||
          Boolean(tasteContext) ||
          Boolean(tasteOrigin);

        if (!isCancelled) {
          setState({
            selectedGenres,
            avoidedGenres,
            savedKeywords,
            savedVibe,
            tasteContext,
            tasteOrigin,
            hasSurveyData,
          });
        }
      } catch (error) {
        const message = error instanceof Error ? error.message : "";
        const isNotFound =
          message.includes("404") ||
          message.toLowerCase().includes("not found");
        if (!isNotFound) {
          console.warn("Failed to load taste survey from server:", error);
        }
        if (!isCancelled) {
          setState(emptySurveyState);
        }
      }
    };

    if (isLoggedIn) {
      setFromServer();
    } else {
      setFromLocal();
    }

    return () => {
      isCancelled = true;
    };
  }, [refreshKey]);

  return state;
};
