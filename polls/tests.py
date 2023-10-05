from django.test import TestCase
import datetime
from django.utils import timezone
from polls.models import Question, Choice
from django.urls import reverse


def create_question(question_text, days):
    return Question.objects.create(question_text=question_text, pub_date=timezone.now() + datetime.timedelta(days=days))


class QuestionModelTests(TestCase):

    def test_was_published_recently_with_future_question(self):
        time = timezone.now() + datetime.timedelta(days=30)
        future_question = Question(pub_date=time)
        self.assertIs(future_question.was_published_recently(), False)

    def test_was_published_recently_with_old_question(self):
        time = timezone.now() - datetime.timedelta(days=1, seconds=1)
        question = Question(pub_date=time)
        self.assertIs(question.was_published_recently(), False)

    def test_was_published_recently_with_recent_question(self):
        time = timezone.now()-datetime.timedelta(hours=23, minutes=59, seconds=59)
        question = Question(pub_date=time)
        self.assertIs(question.was_published_recently(), True)

    def test_no_question(self):
        response = self.client.get(reverse('polls:index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No polls are available.")
        self.assertQuerysetEqual(response.context['latest_question_list'], [])

    def test_past_question(self):
        question = create_question("Past Question", days=-30)
        response = self.client.get(reverse('polls:index'))
        self.assertQuerysetEqual(response.context['latest_question_list'], [question])

    def test_future_question(self):
        create_question("Future Question", days=30)
        response = self.client.get(reverse('polls:index'))
        self.assertContains(response, "No polls are available.")
        self.assertQuerysetEqual(response.context['latest_question_list'], [])

    def test_future_and_past_questions(self):
        question1 = create_question("Past Question", days=-30)
        create_question("Future Question", days=30)
        response = self.client.get(reverse('polls:index'))
        self.assertQuerysetEqual(response.context['latest_question_list'], [question1])

    def test_two_past_questions(self):
        question1 = create_question("question1", days=-4)
        question2 = create_question("question2", days=-30)
        response = self.client.get(reverse('polls:index'))
        self.assertQuerysetEqual(response.context['latest_question_list'], [question1, question2])


class QuestionDetailViewTests(TestCase):

    def test_future_question(self):
        question = create_question("Future question", days=1)
        response = self.client.get(reverse('polls:detail', args=(question.id,)))
        self.assertEqual(response.status_code, 404)

    def test_not_enough_choices_past_question(self):
        question = create_question("Not enough choices question", days=-2)
        response = self.client.get(reverse('polls:detail', args=(question.id,)))
        self.assertContains(response, "don't have enough choices!")
        Choice.objects.create(question_id=question.id)
        response = self.client.get(reverse('polls:detail', args=(question.id,)))
        self.assertContains(response, "don't have enough choices!")

    def test_enough_choices_past_question(self):
        question = create_question("Enough choices question", days=-2)
        Choice.objects.create(question_id=question.id, choice_text='choice1')
        Choice.objects.create(question_id=question.id, choice_text='choice2')
        response = self.client.get(reverse('polls:detail', args=(question.id,)))
        self.assertContains(response, question.question_text)
        for a in range(1, 5):
            Choice.objects.create(question_id=question.id, choice_text='choice2')
        response = self.client.get(reverse('polls:detail', args=(question.id,)))
        self.assertContains(response, question.question_text)

    def test_not_enough_choices_future_question(self):
        question = create_question("Not enough choices question", days=2)
        response = self.client.get(reverse('polls:detail', args=(question.id,)))
        self.assertEqual(response.status_code, 404)
        Choice.objects.create(question_id=question.id)
        response = self.client.get(reverse('polls:detail', args=(question.id,)))
        self.assertEqual(response.status_code, 404)

    def test_enough_choices_future_question(self):
        question = create_question("Enough choices question", days=2)
        Choice.objects.create(question_id=question.id, choice_text='choice1')
        Choice.objects.create(question_id=question.id, choice_text='choice2')
        response = self.client.get(reverse('polls:detail', args=(question.id,)))
        self.assertEqual(response.status_code, 404)
        for a in range(1, 5):
            Choice.objects.create(question_id=question.id, choice_text='choice2')
        response = self.client.get(reverse('polls:detail', args=(question.id,)))
        self.assertEqual(response.status_code, 404)

    def test_vote_valid_choice(self):
        question = create_question("Not enough choices question", days=-2)
        Choice.objects.create(question_id=question.id, choice_text='choice1')
        choice = Choice.objects.create(question_id=question.id, choice_text='choice2')
        response = self.client.post(reverse('polls:vote', args=(question.id,)), {'choice': choice.id})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('polls:results', args=(question.id,)))

    def test_vote_valid_choice_with_enough_choices_past_question(self):
        question = create_question("question", days=-2)
        Choice.objects.create(question_id=question.id, choice_text='choice1')
        choice = Choice.objects.create(question_id=question.id, choice_text='choice2')
        response = self.client.post(reverse('polls:vote', args=(question.id,)), {'choice': choice.id})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('polls:results', args=(question.id,)))

    def test_vote_invalid_choice_with_enough_choices_past_question(self):
        question = create_question("question", days=-2)
        question2 = create_question("question2", days=-2)
        Choice.objects.create(question_id=question.id, choice_text='choice1')
        Choice.objects.create(question_id=question.id, choice_text='choice2')
        choice = Choice.objects.create(question_id=question2.id, choice_text='choice2')
        response = self.client.post(reverse('polls:vote', args=(question.id,)), {'choice': choice.id})
        self.assertEqual(response.status_code, 200)

    def test_vote_valid_choice_with_enough_choices_future_question(self):
        question = create_question("question", days=2)
        Choice.objects.create(question_id=question.id, choice_text='choice1')
        choice = Choice.objects.create(question_id=question.id, choice_text='choice2')
        response = self.client.post(reverse('polls:vote', args=(question.id,)), {'choice': choice.id})
        self.assertEqual(response.status_code, 404)

    def test_vote_invalid_choice_with_enough_choices_future_question(self):
        question = create_question("question", days=2)
        question2 = create_question("question2", days=-2)
        Choice.objects.create(question_id=question.id, choice_text='choice1')
        Choice.objects.create(question_id=question.id, choice_text='choice2')
        choice = Choice.objects.create(question_id=question2.id, choice_text="choice3")
        response = self.client.post((reverse('polls:vote', args=(question.id,)), {'choice': choice.id}))
        self.assertEqual(response.status_code, 404)
