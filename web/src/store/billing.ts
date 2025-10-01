import { enableMapSet, produce } from "immer";
import React from "react";
import { create } from "zustand";
import { createErrorFromResponse } from "@/lib/apiError";
import { apiFetch } from "@/lib/apiFetch";
import {
  AutomaticPaymentRequest,
  CreatePaymentIntentRequest,
  OrganizationSettings,
  PaymentIntentCreatedResponse,
  PaymentMethodRequest,
  PaymentMethodResponse,
} from "@/types/models";

enableMapSet();

interface BillingState {
  // Organization Settings
  organizationSettings: OrganizationSettings | null;
  isLoadingOrganizationSettings: boolean;
  organizationSettingsError: Error | null;

  // Payment Methods
  paymentMethod: PaymentMethodResponse | null;
  isLoadingPaymentMethod: boolean;
  paymentMethodError: Error | null;
  isPaymentMethodInitialized: boolean;

  // Actions
  fetchOrganizationSettings: () => Promise<void>;
  fetchPaymentMethod: () => Promise<void>;
  addPaymentMethod: (paymentMethodId: string) => Promise<void>;
  deletePaymentMethod: () => Promise<void>;
  updateAutomaticPayments: (settings: {
    opt_in: boolean;
    threshold?: number;
    balance_to_maintain?: number;
  }) => Promise<void>;
  createPaymentIntent: (amount: number) => Promise<{ client_secret: string; payment_intent_id: string }>;
}

export const useBillingStore = create<BillingState>((set, get) => ({
  // Initial state
  organizationSettings: null,
  isLoadingOrganizationSettings: false,
  organizationSettingsError: null,

  paymentMethod: null,
  isLoadingPaymentMethod: false,
  paymentMethodError: null,
  isPaymentMethodInitialized: false,

  fetchOrganizationSettings: async () => {
    if (get().isLoadingOrganizationSettings) return;

    set(
      produce((state: BillingState) => {
        state.isLoadingOrganizationSettings = true;
        state.organizationSettingsError = null;
      })
    );

    try {
      const response = await apiFetch("/v1/organization/settings", {
        method: "GET",
      });

      if (!response.ok) {
        throw await createErrorFromResponse(response);
      }

      const settings: OrganizationSettings = await response.json();

      set(
        produce((state: BillingState) => {
          state.organizationSettings = settings;
          state.isLoadingOrganizationSettings = false;
        })
      );
    } catch (error) {
      const errorObj = error as Error & { isApiError?: boolean };
      if (!errorObj.isApiError) {
        console.error("Failed to fetch organization settings:", error);
      }

      set(
        produce((state: BillingState) => {
          state.organizationSettingsError = error as Error;
          state.isLoadingOrganizationSettings = false;
        })
      );
    }
  },

  fetchPaymentMethod: async () => {
    if (get().isLoadingPaymentMethod) return;

    set(
      produce((state: BillingState) => {
        state.isLoadingPaymentMethod = true;
        state.paymentMethodError = null;
      })
    );

    try {
      const response = await apiFetch("/v1/payments/payment-methods", {
        method: "GET",
      });

      if (!response.ok) {
        if (response.status === 404) {
          // No payment method found
          set(
            produce((state: BillingState) => {
              state.paymentMethod = null;
              state.isLoadingPaymentMethod = false;
              state.isPaymentMethodInitialized = true;
            })
          );
          return;
        }
        throw await createErrorFromResponse(response);
      }

      const method: PaymentMethodResponse = await response.json();

      set(
        produce((state: BillingState) => {
          state.paymentMethod = method;
          state.isLoadingPaymentMethod = false;
          state.isPaymentMethodInitialized = true;
        })
      );
    } catch (error) {
      const errorObj = error as Error & { isApiError?: boolean };
      if (!errorObj.isApiError) {
        console.error("Failed to fetch payment method:", error);
      }

      set(
        produce((state: BillingState) => {
          state.paymentMethodError = error as Error;
          state.isLoadingPaymentMethod = false;
          state.isPaymentMethodInitialized = true;
        })
      );
    }
  },

  addPaymentMethod: async (paymentMethodId: string) => {
    try {
      const request: PaymentMethodRequest = {
        payment_method_id: paymentMethodId,
        payment_method_currency: "USD",
      };

      const response = await apiFetch("/v1/payments/payment-methods", {
        method: "POST",
        body: JSON.stringify(request),
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw await createErrorFromResponse(response);
      }

      // Refresh payment method after adding
      await get().fetchPaymentMethod();
    } catch (error) {
      throw error;
    }
  },

  deletePaymentMethod: async () => {
    try {
      const response = await apiFetch("/v1/payments/payment-methods", {
        method: "DELETE",
      });

      if (!response.ok) {
        throw await createErrorFromResponse(response);
      }

      set({ paymentMethod: null });
    } catch (error) {
      throw error;
    }
  },

  updateAutomaticPayments: async (settings) => {
    try {
      const request: AutomaticPaymentRequest = {
        opt_in: settings.opt_in,
        threshold: settings.threshold,
        balance_to_maintain: settings.balance_to_maintain,
      };

      const response = await apiFetch("/v1/payments/automatic-payments", {
        method: "PUT",
        body: JSON.stringify(request),
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw await createErrorFromResponse(response);
      }

      // Refresh organization settings after updating
      await get().fetchOrganizationSettings();
    } catch (error) {
      throw error;
    }
  },

  createPaymentIntent: async (amount: number) => {
    try {
      const request: CreatePaymentIntentRequest = { amount };

      const response = await apiFetch("/v1/payments/payment-intents", {
        method: "POST",
        body: JSON.stringify(request),
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw await createErrorFromResponse(response);
      }

      const result: PaymentIntentCreatedResponse = await response.json();

      // Refresh organization settings after payment
      await get().fetchOrganizationSettings();
      return result;
    } catch (error) {
      throw error;
    }
  },
}));

// Hooks for easy component usage
export const useOrganizationSettings = () => {
  const { organizationSettings, isLoadingOrganizationSettings, organizationSettingsError, fetchOrganizationSettings } =
    useBillingStore();
  return {
    organizationSettings,
    isLoading: isLoadingOrganizationSettings,
    error: organizationSettingsError,
    fetchOrganizationSettings,
  };
};

export const usePaymentMethod = () => {
  const { paymentMethod, isLoadingPaymentMethod, paymentMethodError, isPaymentMethodInitialized, fetchPaymentMethod } =
    useBillingStore();
  return {
    paymentMethod,
    isLoading: isLoadingPaymentMethod,
    error: paymentMethodError,
    isInitialized: isPaymentMethodInitialized,
    fetchPaymentMethod,
  };
};

// Auto-fetching hooks with polling
export const useOrFetchOrganizationSettings = (pollingInterval?: number) => {
  const store = useBillingStore();

  React.useEffect(() => {
    // Initial fetch
    store.fetchOrganizationSettings();

    // Set up polling if interval provided
    if (pollingInterval) {
      const interval = setInterval(() => {
        store.fetchOrganizationSettings();
      }, pollingInterval);

      return () => clearInterval(interval);
    }
  }, [store, pollingInterval]);

  return {
    organizationSettings: store.organizationSettings,
    isLoading: store.isLoadingOrganizationSettings,
    error: store.organizationSettingsError,
  };
};

export const useOrFetchPaymentMethod = (pollingInterval?: number) => {
  const store = useBillingStore();

  React.useEffect(() => {
    // Initial fetch
    store.fetchPaymentMethod();

    // Set up polling if interval provided
    if (pollingInterval) {
      const interval = setInterval(() => {
        store.fetchPaymentMethod();
      }, pollingInterval);

      return () => clearInterval(interval);
    }
  }, [store, pollingInterval]);

  return {
    paymentMethod: store.paymentMethod,
    isLoading: store.isLoadingPaymentMethod,
    isInitialized: store.isPaymentMethodInitialized,
    error: store.paymentMethodError,
  };
};
