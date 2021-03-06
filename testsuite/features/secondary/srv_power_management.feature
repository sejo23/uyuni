# Copyright (c) 2015 SUSE LLC
# Licensed under the terms of the MIT license.

Feature: Power management

  Scenario: Fake an IPMI host
    Given the server starts mocking an IPMI host

  Scenario: Check the power management page
    Given I am on the Systems overview page of this "sle_client"
    And I follow "Provisioning" in the content area
    And I follow "Power Management" in the content area
    Then I should see a "Power Management Settings" text
    And I should see a "IPMI" text
    And I should see a "Save" button

  Scenario: Save power management values
    Given I am on the Systems overview page of this "sle_client"
    And I follow "Provisioning" in the content area
    And I follow "Power Management" in the content area
    When I enter "127.0.0.1" as "powerAddress"
    And I enter "ipmiusr" as "powerUsername"
    And I enter "test" as "powerPassword"
    And I click on "Save"
    Then I should see a "Power settings saved" text
    And the cobbler report contains "Power Management Address       : 127.0.0.1"
    And the cobbler report contains "Power Management Username      : ipmiusr"
    And the cobbler report contains "Power Management Password      : test"
    And the cobbler report contains "Power Management Type          : ipmitool"

  Scenario: Test IPMI functions
    Given I am on the Systems overview page of this "sle_client"
    And I follow "Provisioning" in the content area
    And I follow "Power Management" in the content area
    Then I click on "Power On"
    And I click on "Get status"
    And I should see the power is "On"
    And I click on "Power Off"
    And I should see a "system has been powered off" text
    And I wait for "20" seconds
    And I should see the power is "Unknown"
    Then I click on "Get status"
    And I should see the power is "Off"
    Then I click on "Power On"
    And I should see a "system has been powered on" text
    Then I click on "Get status"
    And I should see the power is "On"
    Then I click on "Reboot"
    And I should see a "system has been rebooted" text
    Then I click on "Get status"
    And I should see the power is "On"

  Scenario: Check power management SSM configuration
    Given I am authorized
    And I am on the System Overview page
    And I check the "sle_client" client
    And I am on System Set Manager Overview
    And I follow "Configure power management" in the content area
    Then I should see "sle_client" as link
    And I should see a "Change Power Management Configuration" text
    And I should see a "Type" text
    And I should see a "Network address" text
    And I should see a "Username" text
    And I should see a "Password" text
    And I should see a "System identifier" text
    And I should see a "Update" button
    When I enter "testing" as "powerUsername"
    And I enter "qwertz" as "powerPassword"
    And I click on "Update"
    Then I should see a "Configuration successfully saved for 1 system(s)" text
    And the cobbler report contains "Power Management Username      : testing"
    And the cobbler report contains "Power Management Password      : qwertz"
    And the cobbler report contains "Power Management Address       : 127.0.0.1"
    And the cobbler report contains "Power Management Type          : ipmitool"

  Scenario: Check power management SSM operation
    Given I am authorized
    And I am on System Set Manager Overview
    And I follow "power management operations" in the content area
    Then I should see "sle_client" as link
    And I should see a "Power On" button
    And I should see a "Power Off" button
    And I should see a "Reboot" button

  Scenario: Cleanup: don't fake an IPMI host
    Given the server stops mocking an IPMI host

  Scenario: Cleanup: remove remaining systems from SSM after power management tests
    When I am authorized as "admin" with password "admin"
    And I follow "Clear"
