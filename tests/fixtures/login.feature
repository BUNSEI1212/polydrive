Feature: Login functionality
  As a user
  I want to log in
  So that I can access the system

  @smoke @critical
  Scenario: Successful login
    Given the user is on the login page
    When the user enters valid credentials
    And the user clicks the login button
    Then the user should be redirected to the dashboard

  @smoke
  Scenario: Invalid password
    Given the user is on the login page
    When the user enters an invalid password
    Then an error message should be displayed

  @regression
  Scenario: Account locked after failed attempts
    Given the user is on the login page
    When the user enters wrong credentials 5 times
    Then the account should be locked
    And a lockout notification should be sent
