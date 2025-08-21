import { enableMapSet, produce } from "immer";
import { useEffect } from "react";
import { create } from "zustand";
import { apiFetch } from "@/lib/apiFetch";
import {
  AutomaticPaymentRequest,
  CreatePaymentIntentRequest,
  OrganizationSettings,
  PaymentIntentCreatedResponse,
  PaymentMethodIdResponse,
  PaymentMethodRequest,
  PaymentMethodResponse,
} from "@/types/models";

enableMapSet();

interface PaymentsState {
  // Payment method state
  paymentMethod: PaymentMethodResponse | null;
  isLoadingPaymentMethod: boolean;
  paymentMethodError: Error | null;
  isPaymentMethodInitialized: boolean;

  // Organization settings state
  organizationSettings: OrganizationSettings | null;
  isLoadingOrganizationSettings: boolean;
  organizationSettingsError: Error | null;
  isOrganizationSettingsInitialized: boolean;

  // Payment operations loading state
  isProcessingPayment: boolean;
  isUpdatingAutomaticPayment: boolean;

  // Actions
  fetchPaymentMethod: () => Promise<void>;
  addPaymentMethod: (paymentMethodId: string, currency?: string) => Promise<PaymentMethodIdResponse | null>;
  deletePaymentMethod: () => Promise<void>;
  createPaymentIntent: (amount: number) => Promise<PaymentIntentCreatedResponse | null>;
  updateAutomaticPayment: (optIn: boolean, threshold: number | null, balanceToMaintain: number | null) => Promise<void>;
  retryAutomaticPayment: () => Promise<void>;

  // Organization settings actions
  fetchOrganizationSettings: () => Promise<void>;

  // Utility actions
  clearErrors: () => void;
  refreshAll: () => Promise<void>;
}

// Mock data for development
const MOCK_PAYMENT_METHOD: PaymentMethodResponse = {
  payment_method_id: "pm_mock_card_visa",
  last4: "4242",
  brand: "visa",
  exp_month: 12,
  exp_year: 2025,
};

const MOCK_ORGANIZATION_SETTINGS: OrganizationSettings = {
  id: "org_mock_123",
  name: "Test Organization",
  slug: "test-org",
  current_credits_usd: 25.5,
  added_credits_usd: 100.0,
  automatic_payment_enabled: true,
  automatic_payment_threshold: 10.0,
  automatic_payment_balance_to_maintain: 50.0,
  payment_failure: null,
  locked_for_payment: false,
  stripe_customer_id: "cus_mock_customer",
};

export const usePayments = create<PaymentsState>((set, get) => ({
  // Initial state
  paymentMethod: null,
  isLoadingPaymentMethod: false,
  paymentMethodError: null,
  isPaymentMethodInitialized: false,

  organizationSettings: null,
  isLoadingOrganizationSettings: false,
  organizationSettingsError: null,
  isOrganizationSettingsInitialized: false,

  isProcessingPayment: false,
  isUpdatingAutomaticPayment: false,

  fetchPaymentMethod: async () => {
    if (get().isLoadingPaymentMethod) return;

    set(
      produce((state: PaymentsState) => {
        state.isLoadingPaymentMethod = true;
        state.paymentMethodError = null;
      })
    );

    try {
      const response = await apiFetch("/v1/organization/payments/payment-methods", {
        method: "GET",
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
      }

      const paymentMethod: PaymentMethodResponse | null = await response.json();

      set(
        produce((state: PaymentsState) => {
          state.paymentMethod = paymentMethod;
          state.isLoadingPaymentMethod = false;
          state.isPaymentMethodInitialized = true;
        })
      );
    } catch (error) {
      // For development, use mock data
      if (process.env.NODE_ENV === "development") {
        set(
          produce((state: PaymentsState) => {
            state.paymentMethod = MOCK_PAYMENT_METHOD;
            state.isLoadingPaymentMethod = false;
            state.isPaymentMethodInitialized = true;
          })
        );
        return;
      }

      set(
        produce((state: PaymentsState) => {
          state.paymentMethodError = error instanceof Error ? error : new Error("Failed to fetch payment method");
          state.isLoadingPaymentMethod = false;
          state.isPaymentMethodInitialized = true;
        })
      );
    }
  },

  addPaymentMethod: async (paymentMethodId: string, currency = "USD") => {
    if (get().isProcessingPayment) return null;

    set(
      produce((state: PaymentsState) => {
        state.isProcessingPayment = true;
        state.paymentMethodError = null;
      })
    );

    try {
      const request: PaymentMethodRequest = {
        payment_method_id: paymentMethodId,
        payment_method_currency: currency,
      };

      const response = await apiFetch("/v1/organization/payments/payment-methods", {
        method: "POST",
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
      }

      const result: PaymentMethodIdResponse = await response.json();

      // Refresh payment method after adding
      await get().fetchPaymentMethod();
      await get().fetchOrganizationSettings();

      set(
        produce((state: PaymentsState) => {
          state.isProcessingPayment = false;
        })
      );

      return result;
    } catch (error) {
      // For development, use mock response
      if (process.env.NODE_ENV === "development") {
        set(
          produce((state: PaymentsState) => {
            state.paymentMethod = MOCK_PAYMENT_METHOD;
            state.isProcessingPayment = false;
          })
        );
        return { payment_method_id: paymentMethodId };
      }

      set(
        produce((state: PaymentsState) => {
          state.paymentMethodError = error instanceof Error ? error : new Error("Failed to add payment method");
          state.isProcessingPayment = false;
        })
      );
      return null;
    }
  },

  deletePaymentMethod: async () => {
    if (get().isProcessingPayment) return;

    set(
      produce((state: PaymentsState) => {
        state.isProcessingPayment = true;
        state.paymentMethodError = null;
      })
    );

    try {
      const response = await apiFetch("/v1/organization/payments/payment-methods", {
        method: "DELETE",
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
      }

      // Refresh payment method and organization settings after deleting
      await get().fetchPaymentMethod();
      await get().fetchOrganizationSettings();

      set(
        produce((state: PaymentsState) => {
          state.isProcessingPayment = false;
        })
      );
    } catch (error) {
      // For development, simulate deletion
      if (process.env.NODE_ENV === "development") {
        set(
          produce((state: PaymentsState) => {
            state.paymentMethod = null;
            state.organizationSettings = state.organizationSettings
              ? {
                  ...state.organizationSettings,
                  automatic_payment_enabled: false,
                  automatic_payment_threshold: null,
                  automatic_payment_balance_to_maintain: null,
                }
              : null;
            state.isProcessingPayment = false;
          })
        );
        return;
      }

      set(
        produce((state: PaymentsState) => {
          state.paymentMethodError = error instanceof Error ? error : new Error("Failed to delete payment method");
          state.isProcessingPayment = false;
        })
      );
    }
  },

  createPaymentIntent: async (amount: number) => {
    if (get().isProcessingPayment) return null;

    set(
      produce((state: PaymentsState) => {
        state.isProcessingPayment = true;
        state.paymentMethodError = null;
      })
    );

    try {
      const request: CreatePaymentIntentRequest = { amount };

      const response = await apiFetch("/v1/organization/payments/payment-intents", {
        method: "POST",
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
      }

      const result: PaymentIntentCreatedResponse = await response.json();

      set(
        produce((state: PaymentsState) => {
          state.isProcessingPayment = false;
        })
      );

      return result;
    } catch (error) {
      // For development, use mock response
      if (process.env.NODE_ENV === "development") {
        set(
          produce((state: PaymentsState) => {
            state.isProcessingPayment = false;
            // Simulate adding credits
            if (state.organizationSettings) {
              state.organizationSettings.current_credits_usd =
                (state.organizationSettings.current_credits_usd || 0) + amount;
              state.organizationSettings.added_credits_usd =
                (state.organizationSettings.added_credits_usd || 0) + amount;
            }
          })
        );
        return {
          client_secret: "pi_mock_secret_12345",
          payment_intent_id: "pi_mock_intent_12345",
        };
      }

      set(
        produce((state: PaymentsState) => {
          state.paymentMethodError = error instanceof Error ? error : new Error("Failed to create payment intent");
          state.isProcessingPayment = false;
        })
      );
      return null;
    }
  },

  updateAutomaticPayment: async (optIn: boolean, threshold: number | null, balanceToMaintain: number | null) => {
    if (get().isUpdatingAutomaticPayment) return;

    set(
      produce((state: PaymentsState) => {
        state.isUpdatingAutomaticPayment = true;
        state.paymentMethodError = null;
      })
    );

    try {
      const request: AutomaticPaymentRequest = {
        opt_in: optIn,
        threshold,
        balance_to_maintain: balanceToMaintain,
      };

      const response = await apiFetch("/v1/organization/payments/automatic-payments", {
        method: "PUT",
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
      }

      // Refresh organization settings after updating
      await get().fetchOrganizationSettings();

      set(
        produce((state: PaymentsState) => {
          state.isUpdatingAutomaticPayment = false;
        })
      );
    } catch (error) {
      // For development, update mock data
      if (process.env.NODE_ENV === "development") {
        set(
          produce((state: PaymentsState) => {
            if (state.organizationSettings) {
              state.organizationSettings.automatic_payment_enabled = optIn;
              state.organizationSettings.automatic_payment_threshold = threshold;
              state.organizationSettings.automatic_payment_balance_to_maintain = balanceToMaintain;
            }
            state.isUpdatingAutomaticPayment = false;
          })
        );
        return;
      }

      set(
        produce((state: PaymentsState) => {
          state.paymentMethodError = error instanceof Error ? error : new Error("Failed to update automatic payment");
          state.isUpdatingAutomaticPayment = false;
        })
      );
    }
  },

  retryAutomaticPayment: async () => {
    if (get().isProcessingPayment) return;

    set(
      produce((state: PaymentsState) => {
        state.isProcessingPayment = true;
        state.paymentMethodError = null;
      })
    );

    try {
      const response = await apiFetch("/v1/organization/payments/automatic-payments/retry", {
        method: "POST",
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
      }

      // Refresh organization settings after retry
      await get().fetchOrganizationSettings();

      set(
        produce((state: PaymentsState) => {
          state.isProcessingPayment = false;
        })
      );
    } catch (error) {
      // For development, clear payment failure
      if (process.env.NODE_ENV === "development") {
        set(
          produce((state: PaymentsState) => {
            if (state.organizationSettings) {
              state.organizationSettings.payment_failure = null;
              state.organizationSettings.locked_for_payment = false;
            }
            state.isProcessingPayment = false;
          })
        );
        return;
      }

      set(
        produce((state: PaymentsState) => {
          state.paymentMethodError = error instanceof Error ? error : new Error("Failed to retry automatic payment");
          state.isProcessingPayment = false;
        })
      );
    }
  },

  fetchOrganizationSettings: async () => {
    if (get().isLoadingOrganizationSettings) return;

    set(
      produce((state: PaymentsState) => {
        state.isLoadingOrganizationSettings = true;
        state.organizationSettingsError = null;
      })
    );

    try {
      const response = await apiFetch("/v1/organization/settings", {
        method: "GET",
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
      }

      const organizationSettings: OrganizationSettings = await response.json();

      set(
        produce((state: PaymentsState) => {
          state.organizationSettings = organizationSettings;
          state.isLoadingOrganizationSettings = false;
          state.isOrganizationSettingsInitialized = true;
        })
      );
    } catch (error) {
      // For development, use mock data
      if (process.env.NODE_ENV === "development") {
        set(
          produce((state: PaymentsState) => {
            state.organizationSettings = MOCK_ORGANIZATION_SETTINGS;
            state.isLoadingOrganizationSettings = false;
            state.isOrganizationSettingsInitialized = true;
          })
        );
        return;
      }

      set(
        produce((state: PaymentsState) => {
          state.organizationSettingsError =
            error instanceof Error ? error : new Error("Failed to fetch organization settings");
          state.isLoadingOrganizationSettings = false;
          state.isOrganizationSettingsInitialized = true;
        })
      );
    }
  },

  clearErrors: () => {
    set(
      produce((state: PaymentsState) => {
        state.paymentMethodError = null;
        state.organizationSettingsError = null;
      })
    );
  },

  refreshAll: async () => {
    await Promise.all([get().fetchPaymentMethod(), get().fetchOrganizationSettings()]);
  },
}));

// Hook for automatic fetching of payment method with loading state
export const useOrFetchPaymentMethod = (refetchInterval?: number) => {
  const paymentMethod = usePayments((state) => state.paymentMethod);
  const isLoading = usePayments((state) => state.isLoadingPaymentMethod);
  const error = usePayments((state) => state.paymentMethodError);
  const isInitialized = usePayments((state) => state.isPaymentMethodInitialized);
  const fetchPaymentMethod = usePayments((state) => state.fetchPaymentMethod);

  useEffect(() => {
    if (!isInitialized) {
      fetchPaymentMethod();
    }
  }, [fetchPaymentMethod, isInitialized]);

  // Optional auto-refresh
  useEffect(() => {
    if (!refetchInterval || !isInitialized) return;

    const interval = setInterval(() => {
      fetchPaymentMethod();
    }, refetchInterval);

    return () => clearInterval(interval);
  }, [fetchPaymentMethod, refetchInterval, isInitialized]);

  return {
    paymentMethod,
    isLoading,
    error,
    isInitialized,
  };
};

// Hook for automatic fetching of organization settings with loading state
export const useOrFetchOrganizationSettings = (refetchInterval?: number) => {
  const organizationSettings = usePayments((state) => state.organizationSettings);
  const isLoading = usePayments((state) => state.isLoadingOrganizationSettings);
  const error = usePayments((state) => state.organizationSettingsError);
  const isInitialized = usePayments((state) => state.isOrganizationSettingsInitialized);
  const fetchOrganizationSettings = usePayments((state) => state.fetchOrganizationSettings);

  useEffect(() => {
    if (!isInitialized) {
      fetchOrganizationSettings();
    }
  }, [fetchOrganizationSettings, isInitialized]);

  // Optional auto-refresh
  useEffect(() => {
    if (!refetchInterval || !isInitialized) return;

    const interval = setInterval(() => {
      fetchOrganizationSettings();
    }, refetchInterval);

    return () => clearInterval(interval);
  }, [fetchOrganizationSettings, refetchInterval, isInitialized]);

  return {
    organizationSettings,
    isLoading,
    error,
    isInitialized,
  };
};

// Combined hook for both payment method and organization settings
export const useOrFetchPayments = (refetchInterval?: number) => {
  const paymentData = useOrFetchPaymentMethod(refetchInterval);
  const organizationData = useOrFetchOrganizationSettings(refetchInterval);

  return {
    paymentMethod: paymentData.paymentMethod,
    organizationSettings: organizationData.organizationSettings,
    isLoading: paymentData.isLoading || organizationData.isLoading,
    isInitialized: paymentData.isInitialized && organizationData.isInitialized,
    errors: {
      paymentMethod: paymentData.error,
      organizationSettings: organizationData.error,
    },
  };
};
