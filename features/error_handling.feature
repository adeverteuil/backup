Feature: Handling of bad parameters
    In order to correct mistakes in parameters passed to backup
    As a user
    I should be able to read useful error messages on the terminal

Scenario: Invalid name
    When I invoke backup with the arguments "foobaz"
    Then I should see "ERROR"
    And the program should exit 1
