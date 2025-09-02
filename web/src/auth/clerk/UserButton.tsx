"use client";

/* eslint-disable no-restricted-imports */
import {
  CreateOrganization,
  OrganizationList,
  useClerk,
  useOrganization,
  useOrganizationList,
  useUser,
} from "@clerk/nextjs";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { ArrowLeftRight, Building, LogOut, Settings, X } from "lucide-react";
import Image from "next/image";
import { useCallback, useEffect, useMemo, useState } from "react";
import PopoverMenu from "@/components/DropdownMenu";
import { Modal } from "@/components/Modal";
import { cn } from "@/lib/cn";

export { SignedIn, SignedOut } from "@clerk/nextjs";

export function UserButton({ className }: { className?: string }) {
  const { isSignedIn, user } = useUser();
  const { organization } = useOrganization();
  const {
    userMemberships,
    userInvitations,
    userSuggestions,
    isLoaded: isOrganizationListLoaded,
  } = useOrganizationList();
  const { signOut, openUserProfile, openOrganizationProfile } = useClerk();
  const [showOrganizationList, setShowOrganizationList] = useState(false);
  const [showCreateOrganization, setShowCreateOrganization] = useState(false);

  // Extract user info
  const firstName = user?.firstName || "";
  const lastName = user?.lastName || "";
  const email = user?.emailAddresses?.[0]?.emailAddress || "";
  const fullName = [firstName, lastName].filter(Boolean).join(" ");

  // Handle sign-out detection and page reload
  useEffect(() => {
    if (isSignedIn === false) {
      window.location.reload();
    }
  }, [isSignedIn]);

  // Organization state logic (similar to WorkflowAI)
  const orgState = useMemo(() => {
    if (organization) return "selected";

    if (!isOrganizationListLoaded) return undefined;

    // If user has any organizations (memberships, invitations, or suggestions), they can switch
    if (userMemberships.data?.length || userInvitations.data?.length || userSuggestions.data?.length)
      return "available";

    // Only show 'unavailable' if user has absolutely no organizational connections
    return "unavailable";
  }, [isOrganizationListLoaded, organization, userInvitations.data, userSuggestions.data, userMemberships.data]);

  const handleManageAccount = useCallback(() => {
    openUserProfile();
  }, [openUserProfile]);

  const handleOrganizationSettings = useCallback(() => {
    openOrganizationProfile();
  }, [openOrganizationProfile]);

  const handleSwitchOrganization = useCallback(() => {
    setShowOrganizationList(true);
  }, []);

  const handleSignOut = useCallback(async () => {
    await signOut();
  }, [signOut]);

  const handleAfterSelectOrganization = useCallback(() => {
    setShowOrganizationList(false);
    window.location.reload();
    return "/completions";
  }, []);

  const handleAfterCreateOrganization = useCallback(() => {
    setShowCreateOrganization(false);
    window.location.reload();
    return "/completions";
  }, []);

  // Keep the exact same visual appearance as before but make it a custom trigger
  const triggerButton = (
    <div className="flex gap-3 px-5 py-3 justify-between items-center hover:bg-gray-100 rounded-[4px] cursor-pointer transition-colors duration-200">
      <div className="w-8 h-8 rounded-full overflow-hidden bg-gray-200 flex items-center justify-center">
        {user?.imageUrl ? (
          <Image
            src={user.imageUrl}
            alt={fullName || email || "User"}
            width={32}
            height={32}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full bg-gray-300 flex items-center justify-center"></div>
        )}
      </div>

      <div className="flex-1 min-w-0">
        {fullName && <div className="text-[13px] font-medium text-gray-900 truncate">{fullName}</div>}
        {email && <div className="text-xs text-gray-500 truncate">{email}</div>}
      </div>
    </div>
  );

  const menuItems = (
    <>
      <DropdownMenu.Item
        onSelect={handleManageAccount}
        className="flex items-center gap-3 w-full px-3 py-2 text-[13px] text-gray-700 hover:bg-gray-100 transition-colors cursor-pointer outline-none"
      >
        <Settings className="w-4 h-4" />
        Manage Account
      </DropdownMenu.Item>

      {orgState === "selected" && (
        <DropdownMenu.Item
          onSelect={handleOrganizationSettings}
          className="flex items-center gap-3 w-full px-3 py-2 text-[13px] text-gray-700 hover:bg-gray-100 transition-colors cursor-pointer outline-none"
        >
          <Building className="w-4 h-4" />
          Organization Settings
        </DropdownMenu.Item>
      )}

      <DropdownMenu.Item
        onSelect={handleSwitchOrganization}
        className="flex items-center gap-3 w-full px-3 py-2 text-[13px] text-gray-700 hover:bg-gray-100 transition-colors cursor-pointer outline-none"
      >
        <ArrowLeftRight className="w-4 h-4" />
        Switch Organization
      </DropdownMenu.Item>

      <DropdownMenu.Separator className="h-px bg-gray-100 my-1" />

      <DropdownMenu.Item
        onSelect={handleSignOut}
        className="flex items-center gap-3 w-full px-3 py-2 text-[13px] text-gray-700 hover:bg-gray-100 transition-colors cursor-pointer outline-none"
      >
        <LogOut className="w-4 h-4" />
        Sign Out
      </DropdownMenu.Item>
    </>
  );

  return (
    <div className={cn("w-full", className)}>
      <PopoverMenu
        trigger={triggerButton}
        align="center"
        className="z-[9999] bg-white border border-gray-200 rounded-md shadow-lg py-1 px-1 min-w-[220px]"
      >
        {menuItems}
      </PopoverMenu>

      <Modal
        isOpen={showOrganizationList}
        onClose={() => setShowOrganizationList(false)}
        backgroundClassName="bg-black/60"
      >
        <div className="relative w-full h-full flex items-center justify-center">
          <button
            onClick={() => setShowOrganizationList(false)}
            className="absolute top-2 right-2 p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded transition-colors z-10 cursor-pointer"
          >
            <X className="w-4.5 h-4.5" />
          </button>
          <OrganizationList
            afterSelectOrganizationUrl={handleAfterSelectOrganization}
            afterSelectPersonalUrl={handleAfterSelectOrganization}
          />
        </div>
      </Modal>

      <Modal
        isOpen={showCreateOrganization}
        onClose={() => setShowCreateOrganization(false)}
        backgroundClassName="bg-black/60"
      >
        <div className="relative w-full h-full flex items-center justify-center">
          <button
            onClick={() => setShowCreateOrganization(false)}
            className="absolute top-2 right-2 p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded transition-colors z-10 cursor-pointer"
          >
            <X className="w-4.5 h-4.5" />
          </button>
          <CreateOrganization afterCreateOrganizationUrl={handleAfterCreateOrganization} skipInvitationScreen={false} />
        </div>
      </Modal>
    </div>
  );
}
