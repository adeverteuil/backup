Feature: Handling of bad parameters
    In order to correct mistakes in parameters passed to backup
    As a user
    I should be able to read useful error messages on the terminal

    Scenario: Invalid name
        When I invoke backup with the arguments "foobaz"
        Then I should see "ERROR"
        And the program should exit 1

    Scenario: Offline or unreachable host
        Given the value of sourcehost in section nullhost is _
        When I invoke backup without parameters
        Then the program should exit 0
        And I should see "Unable to connect to nullhost"
