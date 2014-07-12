@notempfile
Feature: Obtain usage text
    In order to learn about command line usage of backup
    As a user
    I should be able to read usage information on the terminal

    Scenario: Basic usage
        When I invoke backup with the arguments "-h"
        Then I should see "usage: backup ["
        And the program should exit 0

    Scenario: Bad argument
        When I invoke backup with the arguments "-@"
        Then I should see "usage: backup ["
        And the program should exit 2
